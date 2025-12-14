# 🧾 Streamware Accounting Scanner (Dokumenty/Faktury/Paragony)

Ten moduł ma **2 różne tryby pracy**, które często są mylone:

## 1) `sq accounting scan` (one-shot) – lokalna kamera `/dev/video*` albo ekran

To jest tryb „zrób jedno zdjęcie → wybierz najlepsze → OCR → zapis do projektu”.

- **`--source camera`** oznacza **kamerę USB / laptopową** (`/dev/video0`) i używa `ffmpeg`.
- **RTSP nie jest tutaj obsługiwane** (dlatego pojawia się błąd `Failed to capture/find image`).

Przykłady:

```bash
# Lokalna kamera (wymaga /dev/video0 i ffmpeg)
sq accounting scan --source camera --project faktury_2024

# Zrzut ekranu (działa w sesji graficznej)
sq accounting scan --source screen --project faktury_2024

# Analiza pliku
sq accounting analyze --file faktura.jpg --type invoice
```

### Typowe przyczyny błędu `Failed to capture/find image`
- Brak urządzenia `/dev/video0` (brak kamery lub brak uprawnień)
- Brak `ffmpeg`
- Kamera jest zajęta przez inny proces

## 2) `sq accounting web` – web UI + RTSP (zalecane)

To jest docelowy tryb dla **kamer RTSP** oraz pracy „kioskowej” (automatyczne uruchamianie po starcie systemu).

### Uruchomienie z kamerą RTSP z `.env`
Jeśli masz w `.env` ustawione np.:

```ini
SQ_CAMERAS=main|rtsp://user:pass@192.168.1.100:554/stream
SQ_DEFAULT_CAMERA=main
SQ_WEB_PORT=8080
```

to możesz uruchomić:

```bash
sq accounting web --project faktury_2024 --port 8080 --camera main
```

### Uruchomienie bezpośrednio z URL

```bash
sq accounting web --project faktury_2024 --port 8080 --rtsp "rtsp://user:pass@192.168.1.100:554/stream"
```

### Przydatne opcje

```bash
# Nie otwieraj automatycznie przeglądarki
sq accounting web --project faktury_2024 --port 8080 --camera main --no-browser

# Podgląd OpenCV (okno) – przydatne do testów bez web UI
sq accounting preview --source camera
```

## Model hoster connectivity check (PaddleX)

Jeśli widzisz komunikat:

`Checking connectivity to the model hosters...`

to ustaw:

```bash
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
```

W kodzie Streamware jest to domyślnie ustawiane, ale na niektórych środowiskach warto wymusić w shellu.

## Kluczowe pliki w repo (mapa)

- `streamware/accounting_web.py` – logika web UI + integracja z `.env`
- `streamware/frame_capture.py` – capture: screen/camera/rtsp (PyAV/OpenCV)
- `streamware/detection_mixin.py` – szybka detekcja dokumentu
- `streamware/scanner_config.py` – ładowanie `.env` i ustawień skanera
- `streamware/components/accounting.py` – implementacja `sq accounting scan/analyze/...`
- `environments/usb-builder/build-usb-hybrid.sh` – budowa USB + autostart/kiosk
