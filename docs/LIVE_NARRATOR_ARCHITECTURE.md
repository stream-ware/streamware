# 🎬 Live Narrator - Architektura i Optymalizacje

## Przegląd Systemu

Live Narrator to komponent Streamware do analizy strumieni wideo w czasie rzeczywistym z wykorzystaniem AI (LLM).

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   RTSP      │────▶│  FastCapture │────▶│ SmartDetect │────▶│  Vision LLM  │
│   Stream    │     │  (FFmpeg/CV) │     │ (HOG+Motion)│     │  (moondream) │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                           │                    │                    │
                           ▼                    ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
                    │   RAM Disk   │     │   Cache     │     │  Guarder LLM │
                    │ /dev/shm/    │     │  (images)   │     │  (gemma:2b)  │
                    └──────────────┘     └─────────────┘     └──────────────┘
                                                                    │
                                                                    ▼
                                                             ┌──────────────┐
                                                             │    TTS       │
                                                             │  (pyttsx3)   │
                                                             └──────────────┘
```

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LIVE NARRATOR PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────┘

1. CAPTURE STAGE
   ┌──────────┐    ┌──────────────┐    ┌──────────────┐
   │  RTSP    │───▶│ FastCapture  │───▶│  RAM Disk    │
   │  Stream  │    │ (OpenCV/FFmpeg)│   │ /dev/shm/   │
   └──────────┘    └──────────────┘    └──────────────┘
                          │
                          ▼
2. DETECTION STAGE        
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │   Frame      │───▶│ Motion Detect│───▶│ HOG Person   │
   │   Buffer     │    │  (diff %)    │    │  Detection   │
   └──────────────┘    └──────────────┘    └──────────────┘
                                                  │
                                                  ▼
3. TRACKING STAGE (NEW)
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │ Motion       │───▶│ Object       │───▶│ Tracked      │
   │ Regions      │    │ Tracker      │    │ Objects      │
   └──────────────┘    └──────────────┘    └──────────────┘
         │                    │                    │
         │              ┌─────┴─────┐              │
         │              │ IoU Match │              │
         │              │ ID Assign │              │
         │              │ Direction │              │
         │              └───────────┘              │
         ▼                                         ▼
4. ANALYSIS STAGE
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │ Movement     │───▶│ Vision LLM   │───▶│ Description  │
   │ Context      │    │ (moondream)  │    │ (verbose)    │
   └──────────────┘    └──────────────┘    └──────────────┘
                                                  │
                                                  ▼
5. FILTER STAGE
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │ Verbose      │───▶│ Guarder LLM  │───▶│ Short        │
   │ Description  │    │ (gemma:2b)   │    │ Summary      │
   └──────────────┘    └──────────────┘    └──────────────┘
                                                  │
                                                  ▼
6. OUTPUT STAGE
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │  Filtered    │───▶│    TTS       │───▶│    Log       │
   │  Response    │    │  (pyttsx3)   │    │  (CSV/TXT)   │
   └──────────────┘    └──────────────┘    └──────────────┘
```

## Komponenty

### 1. FastCapture (`fast_capture.py`)
Zoptymalizowany moduł przechwytywania klatek z RTSP.

**Cechy:**
- **Persistent connection** - jedno połączenie FFmpeg/OpenCV zamiast nowego na każdą klatkę
- **GPU acceleration** - NVDEC dla NVIDIA GPU
- **Backend selection** - automatyczny wybór: OpenCV (szybszy) lub FFmpeg (bardziej kompatybilny)
- **Frame buffering** - kolejka 10 klatek dla wolniejszego przetwarzania
- **RAM disk I/O** - `/dev/shm/streamware` dla szybkiego zapisu

**Wydajność:**
| Przed | Po |
|-------|-----|
| ~4000ms/klatkę | **0ms** (z bufora) |

### 2. SmartDetector (`smart_detector.py`)
Inteligentna detekcja obiektów z YOLO i fallback na HOG.

**Pipeline:**
```
Frame → Motion Detection → YOLO Detection → [fallback] HOG → [opcjonalnie] Small LLM
              ↓                  ↓                ↓                    ↓
          <0.5% change?     Auto-installed    No YOLO?          Not vision model?
              ↓                  ↓                ↓                    ↓
            SKIP          Fast & Accurate    Use HOG            ASSUME PRESENT
```

**YOLO Detection (NEW - domyślnie włączone):**
- **Auto-instalacja** - `ultralytics` instalowane przy pierwszym użyciu
- **Modele** - yolov8n (6MB, ~10ms), yolov8s, yolov8m, yolov8l, yolov8x
- **GPU acceleration** - CUDA gdy dostępne
- **80+ klas** - person, car, dog, cat, bicycle, etc.

**Kluczowe optymalizacje:**
- **YOLO first** - szybszy i dokładniejszy niż HOG (~10ms vs ~100ms)
- **Motion threshold** - skipuje klatki bez ruchu (<0.5%)
- **HOG fallback** - gdy YOLO niedostępne
- **Consecutive skip** - co 5 klatkę weryfikuje aby nie przegapić

**Porównanie detektorów:**
| Detektor | Czas | Dokładność | Wymaga GPU |
|----------|------|------------|------------|
| YOLO (yolov8n) | ~10ms | ★★★★★ | Nie (szybszy z) |
| HOG (OpenCV) | ~100ms | ★★★ | Nie |
| Small LLM | ~500ms | ★★★★ | Nie |

### 3. Vision LLM (`moondream`)
Główny model do analizy obrazu.

**Wybór modelu:**
| Model | Czas | Jakość | RAM |
|-------|------|--------|-----|
| moondream | ~1.5s | ★★★ | 2GB |
| llava:7b | ~2-3s | ★★★★ | 4GB |
| llava:13b | ~4-5s | ★★★★★ | 8GB |

**Prompt optymalizacje:**
- Prosty, bezpośredni prompt bez przykładów do kopiowania
- Instrukcje "Describe what you see" zamiast szablonów
- Kontekst z analizy ruchu dla lepszej dokładności

### 4. Guarder LLM (`gemma:2b`)
Filtr i sumaryzator odpowiedzi tekstowych.

**Funkcje:**
- Skraca verbose odpowiedzi do 1 zdania
- Filtruje powtórzenia ("NO_CHANGE")
- Usuwa preambuły LLM ("Sure, here is...")
- Porównuje z poprzednim opisem aby wykryć zmiany

**UWAGA:** `gemma:2b` NIE jest modelem wizyjnym - nie używać do analizy obrazów!

**Prompt dla guardera:**
```
Summarize in max 8 words. Focus: person.
Input: [verbose LLM response]
Output format: "Person: [what they're doing]" or "No person visible"
```

### 5. Object Tracker (`object_tracker.py`) 🆕
Moduł śledzenia wielu obiektów między klatkami.

**Architektura:**
```
Motion Regions → Extract Detections → IoU Association → Track Objects
                                            ↓
                              ┌─────────────┴─────────────┐
                              │    Tracked Object #1      │
                              │    - ID: 1                │
                              │    - Position: (0.3, 0.5) │
                              │    - Direction: moving_right │
                              │    - State: tracked       │
                              │    - History: [...]       │
                              └───────────────────────────┘
```

**Cechy:**
- **Persistent IDs** - obiekty zachowują ID między klatkami
- **Multi-object** - śledzenie wielu obiektów jednocześnie
- **IoU matching** - dopasowanie przez Intersection over Union
- **Trajectory** - historia 30 ostatnich pozycji
- **Zone detection** - left/center/right, top/middle/bottom
- **Entry/exit events** - wykrywanie wejść i wyjść

**Kierunki ruchu:**
| Direction | Opis |
|-----------|------|
| `entering` | Obiekt pojawił się w kadrze |
| `exiting` | Obiekt wychodzi z kadru |
| `moving_left` | Ruch w lewo |
| `moving_right` | Ruch w prawo |
| `approaching` | Zbliża się do kamery |
| `leaving` | Oddala się od kamery |
| `stationary` | Brak ruchu |

**Stany obiektu:**
| State | Opis |
|-------|------|
| `new` | Właśnie pojawił się |
| `tracked` | Aktywnie śledzony |
| `lost` | Tymczasowo zgubiony (max 5 klatek) |
| `gone` | Opuścił kadr |

**Przykład wyjścia:**
```
2 objects tracked. #1: Person moving right in center_middle. #2: Person stationary in left_bottom. Person #3 left.
```

### 6. Cache System

**DescriptionCache** (pamięć RAM):
- Cache opisów podobnych klatek
- Perceptual hash (średnia pikseli 16x16)
- Max 100 wpisów (LRU)
- Unika powtórnych wywołań LLM

**Frame Cache** (ramdisk `/dev/shm/streamware`):
- Klatki JPEG dla FastCapture
- Max 10 klatek (stare usuwane)
- ~10x szybszy niż SSD

## Optymalizacje Wydajności

### Zaimplementowane ✅

1. **FastCapture** - persistent RTSP connection
   - Przed: 4000ms/klatkę
   - Po: 0ms (z bufora)

2. **RAM Disk** - `/dev/shm/streamware`
   - Eliminuje I/O na dysk
   - ~10x szybszy zapis/odczyt

3. **Szybki model wizyjny** - `moondream`
   - 2-3x szybszy niż llava:13b
   - Wystarczająca jakość dla real-time

4. **Szybki guarder** - `gemma:2b`
   - ~200-300ms zamiast ~2-3s
   - Tylko do tekstu, nie obrazów

5. **Image optimization**
   - Resize do 384px dla moondream
   - JPEG quality 75%
   - ~50ms przetwarzania

6. **Smart caching**
   - Cache opisów podobnych klatek
   - Unika powtórnych wywołań LLM

7. **Parallel processing**
   - 8 workerów dla zadań I/O
   - Capture + process w pipeline

### Zaimplementowane ✅ (Nowe)

8. **Animal Detector** (`animal_detector.py`)
   - Wykrywanie ptaków, kotów, psów, dzikich zwierząt
   - YOLO z optymalizacją dla małych obiektów (ptaki)
   - Klasyfikacja zachowań (eating, flying, resting)
   - Bird Feeder Monitor - liczenie wizyt, statystyki

### Planowane 📋

1. **DeepSORT/ByteTrack** - zaawansowane trackery z re-identyfikacją
2. **GPU batching** - przetwarzanie wielu klatek jednocześnie na GPU
3. **Streaming inference** - strumieniowe odpowiedzi z LLM
4. **ONNX/TensorRT** - zoptymalizowane modele detekcji
5. **WebSocket output** - real-time streaming wyników
6. **Multi-camera** - równoległe strumienie z wielu kamer
7. **Zone alerts** - alerty przy przekroczeniu linii/strefy
8. **Bird species identification** - rozpoznawanie gatunków ptaków

## Konfiguracja

### Wymagane modele (auto-instalacja)
```bash
# Instalowane automatycznie przy pierwszym uruchomieniu
ollama pull moondream    # Vision model (~1.7GB)
ollama pull gemma:2b     # Guarder model (~1.7GB)
```

### Zmienne środowiskowe (.env)
```bash
# Modele
SQ_MODEL=moondream
SQ_GUARDER_MODEL=gemma:2b

# Stream
SQ_STREAM_MODE=track
SQ_STREAM_FOCUS=person
SQ_STREAM_INTERVAL=3

# Optymalizacje
SQ_FAST_CAPTURE=true
SQ_RAMDISK_ENABLED=true
SQ_RAMDISK_PATH=/dev/shm/streamware
```

## Użycie

### Podstawowe
```bash
sq live narrator --url "rtsp://user:pass@ip:554/stream" --mode track --focus person --tts
```

### Z pełnym logowaniem
```bash
sq live narrator --url "rtsp://..." --mode track --focus person --tts --verbose
```

### Z zapisem do pliku
```bash
sq live narrator --url "rtsp://..." --file report.html --frames-dir ./frames
```

## Metryki Wydajności

### Typowy cykl (z optymalizacjami)
```
capture:      ~0ms (FastCapture buffer)
smart_detect: ~300ms (HOG + motion)
vision_llm:   ~1500ms (moondream)
guarder_llm:  ~250ms (gemma:2b)
─────────────────────────────────
Total:        ~2s/frame
Throughput:   ~0.5 FPS
```

### Porównanie przed/po
| Etap | Przed | Po | Poprawa |
|------|-------|-----|---------|
| capture | 4000ms | 0ms | 100% |
| vision_llm | 4000ms | 1500ms | 62% |
| guarder_llm | 2700ms | 250ms | 91% |
| **Total** | **10s** | **2s** | **80%** |

## Troubleshooting

### Problem: `llm_no_person` mimo osoby na obrazie
**Przyczyna:** Guarder model (gemma:2b) nie jest wizyjny
**Rozwiązanie:** Zaktualizuj do najnowszej wersji - naprawione automatycznie

### Problem: LLM zwraca `[Action]. [Direction/Position]`
**Przyczyna:** Stary cache z przykładami z promptu
**Rozwiązanie:** `rm -f /dev/shm/streamware/*.jpg`

### Problem: Wolny capture (~4000ms)
**Przyczyna:** Fallback do subprocess FFmpeg
**Rozwiązanie:** Sprawdź czy FastCapture działa: `SQ_FAST_CAPTURE=true`

## Autorzy

- Streamware Team
- Optymalizacje: Dec 2024
