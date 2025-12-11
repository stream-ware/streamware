# Motion Analysis Player - Session Documentation

## Podsumowanie sesji (2025-12-11)

### Cel
Refaktoryzacja HTML dla motion analysis - stworzenie modularnego, lekkiego playera opartego o DSL.

---

## Utworzone pliki

### 1. Static Assets
- **`streamware/static/motion_player.css`** (4KB) - Reużywalne style
- **`streamware/static/motion_player.js`** (13KB) - Parser DSL + renderer SVG

### 2. Python Modules
- **`streamware/llm_motion_prompt.py`** - Generator kompaktowych promptów dla LLM
- **`streamware/async_llm.py`** - Async LLM inference (non-blocking)
- **`streamware/realtime_dsl_server.py`** - WebSocket server dla real-time animacji

### 3. Documentation
- **`docs/MOTION_ANALYSIS_IMPROVEMENTS.md`** - Plan ulepszeń
- **`prompts/motion_analysis_prompt.txt`** - Template promptu dla LLM

---

## Zmiany w istniejących plikach

### `frame_diff_dsl.py`
- Dodano `background_base64` do `FrameDelta` - thumbnails 128px
- Dodano `_capture_thumbnail()` - przechwytywanie podczas analizy
- Dodano filtrowanie statycznych obiektów:
  - `min_velocity=0.01` - min prędkość
  - `max_blob_size_ratio=0.7` - filtruj duże bloby (tło)
  - `min_moving_frames=2` - min klatki z ruchem

### `dsl_visualizer.py`
- Dodano `generate_dsl_html_lightweight()` - lekki HTML z DSL
- Dodano `resize_frame_to_base64()` - resize do 128px

### `live_narrator.py`
- Dodano `--realtime` - WebSocket streaming
- Dodano `--dsl-only` - tryb bez LLM (~1 FPS)
- Dodano `--async_llm` - non-blocking inference
- Dodano cleanup handler dla Ctrl+C

### `response_filter.py`
- Zoptymalizowano `_build_tracking_context()` - kompaktowy format (~60B)
- Integracja z `llm_motion_prompt.py`

### `quick_cli.py`
- Dodano `--realtime` flag
- Dodano `--dsl-only` flag
- Auto-selekcja modelu w `--fast` mode

---

## Optymalizacje wydajności

| Optymalizacja | Wynik |
|---------------|-------|
| Rozmiar HTML | 200KB → 40KB (**80% mniej**) |
| Tracking context | 500B → 60B (**88% mniej**) |
| False positives | 19 → 2 obiektów (**90% mniej**) |
| LLM prompt | 2KB → 341B (**83% mniej**) |

### Tryby pracy

| Tryb | FPS | Opis |
|------|-----|------|
| Standard (llava:7b) | 0.1 | Pełna analiza z LLM |
| Fast (moondream) | 0.3 | Mniejszy model |
| DSL-only | 1.0 | Tylko OpenCV, bez LLM |
| DSL-only + realtime | 2.0 | Real-time w przeglądarce |

---

## Użycie

### Podstawowe
```bash
# Standard - pełna analiza
sq live narrator --url "rtsp://..." --mode track

# Fast - auto mniejszy model
sq live narrator --url "rtsp://..." --mode track --fast

# Turbo - skip checks + fast
sq live narrator --url "rtsp://..." --mode track --turbo
```

### Real-time
```bash
# Real-time viewer w przeglądarce
sq live narrator --url "rtsp://..." --mode track --realtime

# Najszybszy - DSL only
sq live narrator --url "rtsp://..." --mode track --dsl-only --realtime

# Otwórz: http://localhost:8766
```

### Wymuszenie modelu
```bash
sq live narrator --url "rtsp://..." --model moondream
sq live narrator --url "rtsp://..." --model llava:7b
```

---

## Znane problemy

### 1. Filtrowanie zbyt agresywne
Przy statycznej scenie może pokazywać `regions=0`. Rozwiązanie:
- Zmniejszyć `min_velocity` w `FrameDiffAnalyzer`
- Ustawić `filter_static=False`

### 2. GPU wykorzystanie
- OpenCV: CPU only (brak CUDA w buildzie)
- YOLO/Ollama: GPU (RTX 4060)
- Bottleneck: LLM inference (~5-8s)

### 3. Task pending warning
Przy szybkim Ctrl+C może pojawić się warning o pending task.
Nie wpływa na działanie.

---

## Architektura

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ RTSP Camera │────▶│ FrameDiffAnalyzer│────▶│   FrameDelta    │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                      │
                    ┌──────────────────┐              │
                    │  DSL Generator   │◀─────────────┘
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
┌─────────────────┐ ┌───────────────┐ ┌───────────────────┐
│ WebSocket Server│ │ HTML Generator│ │ LLM Analysis      │
│ (realtime)      │ │ (lightweight) │ │ (async)           │
└─────────────────┘ └───────────────┘ └───────────────────┘
          │
          ▼
┌─────────────────┐
│ Browser Player  │
│ :8766           │
└─────────────────┘
```

---

## DSL Format

```
FRAME 1 @ 16:35:29.835
  DELTA motion_pct=2.3% regions=3
  BLOB id=1 pos=(0.5,0.5) size=(0.1,0.2) vel=(0.05,0.03)
  EDGE blob=1 points=127 area=1042px complexity=0.31
  EVENT type=MOVE blob=1 dir=RIGHT speed=0.058
  TRACK blob=1 frames=5 dist=0.25 speed=0.05
```

### Pola
- `DELTA` - podsumowanie klatki (motion %, regiony)
- `BLOB` - wykryty obiekt (pozycja, rozmiar, prędkość)
- `EDGE` - kontury (punkty, obszar, złożoność)
- `EVENT` - zdarzenie (APPEAR, MOVE, EXIT, ENTER)
- `TRACK` - historia śledzenia

---

## LLM Prompt Format (kompaktowy)

```
MOTION_ANALYSIS
Duration: 15s | Frames: 4 | Objects: 3 | Scene: low_activity

OBJECTS:
  #1: F1-4, R→D→L, dist=0.25, moving
  #2: F2-4, D→U, dist=0.11, moving

TIMELINE:
  F1: HIGH +#1
  F2: LOW [#1R #2L] ENTER:#3
  F3: LOW [#1D #3U] EXIT:#2

Question: Is there a person?
```

**Rozmiar: 341B** (vs 2KB verbose)
