# LLM Station dla UM790 Pro

Offline środowisko LLM z obsługą GPU AMD Radeon 780M (RDNA3) uruchamiane z USB.

## 📋 Spis treści

- [Wymagania sprzętowe](#wymagania-sprzętowe)
- [Architektura](#architektura)
- [Szybki start](#szybki-start)
- [Środowisko 1: Ollama + Open-WebUI](#środowisko-1-ollama--open-webui)
- [Środowisko 2: llama.cpp + ROCm](#środowisko-2-llamacpp--rocm)
- [Tworzenie bootowalnego USB](#tworzenie-bootowalnego-usb)
- [Porównanie wydajności](#porównanie-wydajności)

## Wymagania sprzętowe

| Komponent | Specyfikacja |
|-----------|--------------|
| **CPU** | AMD Ryzen 9 7940HS (UM790 Pro) |
| **GPU** | AMD Radeon 780M (RDNA3, 12 CU) |
| **RAM** | 16GB DDR5 |
| **USB** | 64GB USB 3.2 |
| **Wyświetlacz** | HDMI/USB4, max 4K |

## Architektura

```
┌─────────────────────────────────────────────────┐
│              USB 64GB (bootowalne)               │
├─────────────────────────────────────────────────┤
│  Linux (Fedora/Ubuntu) → ładowany do RAM        │
├─────────────────────────────────────────────────┤
│  ├─ Podman                                      │
│  ├─ ROCm drivers (GPU offload)                  │
│  ├─ Ollama (port 11434) lub llama.cpp (8080)    │
│  ├─ Open-WebUI (port 3000)                      │
│  └─ Pre-downloaded models (~20-40GB)            │
├─────────────────────────────────────────────────┤
│  HDMI/USB4 → Wyświetlacz 4K                     │
└─────────────────────────────────────────────────┘
```

## Szybki start

### Na istniejącym systemie (bez USB)

```bash
# 1. Sklonuj/przejdź do katalogu
cd environments/ollama-webui

# 2. Skonfiguruj hosta (jednorazowo)
sudo ./setup-host.sh

# 3. Pobierz modele (wymaga internetu)
./download-models.sh

# 4. Uruchom
./start.sh

# 5. Otwórz przeglądarkę
xdg-open http://localhost:3000
```

### Tworzenie bootowalnego USB (offline)

```bash
# 1. Przygotuj wszystkie zasoby (wymaga internetu)
cd environments/usb-builder
./prepare-offline.sh

# 2. Utwórz bootowalne USB
sudo ./build-usb.sh /dev/sdX

# 3. Boot z USB na UM790 Pro
# 4. System uruchomi się automatycznie
```

---

## Środowisko 1: Ollama + Open-WebUI

**Zalecane dla:** Łatwości użycia, stabilności, wielu modeli jednocześnie.

### Struktura

```
ollama-webui/
├── docker-compose.yml    # Konfiguracja kontenerów
├── setup-host.sh         # Instalacja ROCm na hoście
├── download-models.sh    # Pobieranie modeli
├── start.sh              # Uruchomienie
├── stop.sh               # Zatrzymanie
├── models/               # Modele Ollama (auto)
└── webui-data/           # Dane Open-WebUI
```

### Porty

| Usługa | Port | URL |
|--------|------|-----|
| Ollama API | 11434 | http://localhost:11434 |
| Open-WebUI | 3000 | http://localhost:3000 |

### Polecenia

```bash
# Start
./start.sh

# Stop
./stop.sh

# Sprawdź status
podman ps

# Logi
podman logs ollama
podman logs open-webui

# Dodaj model (online)
podman exec ollama ollama pull llama3.2:3b

# Lista modeli
podman exec ollama ollama list
```

### Zalecane modele dla 16GB RAM

| Model | Rozmiar | Przypadek użycia |
|-------|---------|------------------|
| llama3.2:3b | ~2GB | Szybkie odpowiedzi |
| phi3:mini | ~2GB | Microsoft, szybki |
| mistral:7b | ~4GB | Zbalansowany |
| codellama:7b | ~4GB | Programowanie |

---

## Środowisko 2: llama.cpp + ROCm

**Zalecane dla:** Maksymalnej wydajności, pełnej kontroli, benchmarków.

### Struktura

```
llama-cpp-rocm/
├── Dockerfile            # Obraz z ROCm + llama.cpp
├── docker-compose.yml    # Konfiguracja
├── download-models.sh    # Pobieranie GGUF
├── start.sh              # Uruchomienie
├── stop.sh               # Zatrzymanie
├── benchmark.sh          # Test wydajności
└── models/               # Modele GGUF
    └── model.gguf        # Symlink do domyślnego
```

### Porty

| Usługa | Port | URL |
|--------|------|-----|
| llama-server API | 8080 | http://localhost:8080 |
| OpenAI-compatible | 8080 | http://localhost:8080/v1 |

### Polecenia

```bash
# Start (domyślny model)
./start.sh

# Start z konkretnym modelem
./start.sh mistral-7b-q4.gguf

# Benchmark
./benchmark.sh

# Test API
curl http://localhost:8080/v1/models

# Chat
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello!"}]}'
```

### Zalecane modele GGUF (Q4_K_M)

| Model | Rozmiar | Tokeny/s (780M) |
|-------|---------|-----------------|
| Llama 3.2 3B | ~2GB | 15-25 t/s |
| Phi-3 Mini | ~2GB | 15-25 t/s |
| Mistral 7B | ~4GB | 8-12 t/s |
| CodeLlama 7B | ~4GB | 8-12 t/s |

---

## Tworzenie bootowalnego USB

### Przygotowanie (wymaga internetu)

```bash
cd environments/usb-builder

# 1. Pobierz wszystko na offline
./prepare-offline.sh

# To pobierze:
# - Obrazy kontenerów (~8GB)
# - Modele Ollama (~10-20GB)
# - Modele GGUF (~10-20GB)
```

### Tworzenie USB

```bash
# Znajdź USB (np. /dev/sdb)
lsblk

# Utwórz USB (UWAGA: kasuje dane!)
sudo ./build-usb.sh /dev/sdX
```

### Tworzenie ISO (dla Balena Etcher)

```bash
# Utwórz bootowalne ISO
sudo ./build-iso.sh

# ISO zostanie zapisane w:
# environments/usb-builder/output/llm-station-um790pro.iso

# Użyj z Balena Etcher:
# 1. Otwórz Balena Etcher
# 2. Wybierz plik ISO
# 3. Wybierz dysk USB
# 4. Flash!
```

### Bootowanie na UM790 Pro

1. Włóż USB do UM790 Pro
2. Wejdź do BIOS (F2/Del podczas startu)
3. Ustaw boot z USB
4. System załaduje się do RAM
5. Przeglądarka otworzy się automatycznie

### Pierwszy boot (jednorazowo)

```bash
# Na USB-bootowanym systemie
sudo /run/media/*/LLM_DATA/setup-first-boot.sh
sudo /run/media/*/LLM_DATA/usb-builder/install-autostart.sh
```

---

## Porównanie wydajności

### vLLM vs Ollama vs llama.cpp na 780M

| Aspekt | vLLM | Ollama | llama.cpp |
|--------|------|--------|-----------|
| ROCm 780M | ⚠️ Problematyczne | ✅ Natywne | ✅ Stabilne |
| Łatwość użycia | ❌ Trudne | ✅ Łatwe | ⚡ Średnie |
| Wydajność 7B | ~5 t/s | ~8-10 t/s | ~8-12 t/s |
| Multi-model | ✅ | ✅ | ❌ |
| Pamięć | Wysoka | Średnia | Niska |

### Rekomendacja

- **Codzienne użycie:** Ollama + Open-WebUI
- **Maksymalna wydajność:** llama.cpp
- **Unikaj:** vLLM na RDNA3 (niestabilne)

---

## Rozwiązywanie problemów

### GPU nie wykryte

```bash
# Sprawdź urządzenia
ls -la /dev/kfd /dev/dri

# Sprawdź ROCm
rocm-smi --showproductname

# Dodaj użytkownika do grupy video
sudo usermod -aG video $USER
# Wyloguj i zaloguj ponownie
```

### Błędy ROCm na 780M

```bash
# Ustaw wersję GFX (RDNA3 = 11.0.0)
export HSA_OVERRIDE_GFX_VERSION=11.0.0
```

### Kontener nie startuje

```bash
# Sprawdź logi
podman logs ollama
podman logs llama-server

# Restart
./stop.sh && ./start.sh
```

### Brak pamięci

```bash
# Użyj mniejszego modelu
# Ollama:
podman exec ollama ollama pull phi3:mini

# llama.cpp:
./start.sh phi-3-mini-q4.gguf
```

---

## Licencja

MIT License - zobacz główny plik LICENSE projektu.
