# Streamware TODO

## ✅ COMPLETED (2024-11-29)

### Dokumentacja przeniesiona do docs/
- [x] `docs/v1/` - archiwalne dokumenty (summaries, fixes, status) 
- [x] `docs/v2/` - aktualne dokumenty (guides, components)
- [x] `docs/v2/README.md` - główny index dokumentacji z quick reference

### LLM Component zaktualizowany (LiteLLM-compatible)
- [x] Format provider: `"openai/gpt-4o"`, `"ollama/qwen2.5:14b"`, `"groq/llama3-70b-8192"`
- [x] Auto-detekcja kluczy API z env (OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY, etc.)
- [x] Obsługa 10+ providerów: openai, anthropic, ollama, gemini, groq, deepseek, mistral, cohere, together, fireworks
- [x] Fallback do Ollama gdy brak klucza API
- [x] Auto-install litellm dla niestandardowych providerów
- [x] Obsługa custom base_url dla proxy/local deployments

### Examples zaktualizowane
- [x] `examples/llm_examples.py` używa nowego formatu provider/model

### Testy
- [x] 106 passed, 6 skipped, 0 failed

## Supported Providers

```python
# Format: provider/model
provider="openai/gpt-4o"           # OPENAI_API_KEY
provider="anthropic/claude-3-5-sonnet-20240620"  # ANTHROPIC_API_KEY
provider="ollama/qwen2.5:14b"      # local, no key needed
provider="gemini/gemini-2.0-flash" # GEMINI_API_KEY
provider="groq/llama3-70b-8192"    # GROQ_API_KEY
provider="deepseek/deepseek-chat"  # DEEPSEEK_API_KEY
provider="mistral/mistral-large-latest"  # MISTRAL_API_KEY
```

## TODO (Future) - Priority Order

### 🔴 HIGH PRIORITY - User Experience

- [ ] **Web Panel** - `sq web` uruchamia panel konfiguracyjny w przeglądarce
  - Dashboard z podglądem kamer
  - Konfiguracja alertów (Slack, Telegram, Email)
  - Zarządzanie strefami (drag & drop)
  - Live monitoring z wizualizacją zmian
  
- [ ] **Desktop App** - Electron/Tauri app z tray icon
  - Powiadomienia systemowe
  - Quick access do ustawień
  - Auto-start z systemem

- [x] **Live Narrator (TTS)** - `sq live --tts` ✅ DONE
  - Real-time opis co dzieje się na obrazie
  - Alertowanie głosowe ("Widzę osobę przy drzwiach")
  - Konfiguracja triggerów tekstowych
  - Tryby: full, diff, track

### 🟡 MEDIUM PRIORITY - Detection Quality

- [x] **Lepsze domyślne parametry** - `sq watch` z presetami ✅ DONE
  - Presety: sensitivity (ultra/high/medium/low/minimal)
  - Presety: detect (person/vehicle/motion/package)
  - Presety: speed (realtime/fast/normal/slow)

- [ ] **Object persistence tracking**
  - Śledzenie obiektów między klatkami
  - Wykrywanie: "osoba weszła/wyszła"
  - Zliczanie unikalnych obiektów

- [x] **Trigger system** - `sq live watch --trigger` ✅ PARTIAL
  - "alert gdy osoba przy drzwiach"
  - "powiadom gdy paczka na progu"
  - Brakuje: nagrywanie przy triggerze

### 🟢 LOW PRIORITY - Infrastructure

- [ ] Auto-install zależności (PyAudio, xdotool, Pillow, numpy)
- [ ] Dokumentacja API dla wszystkich komponentów
- [ ] LLMConfig class dla advanced configuration
- [ ] Więcej przykładów sq w examples/
- [ ] Plugin system dla custom components
- [ ] REST API server mode (`sq serve`)
- [ ] MQTT integration dla IoT

### 📋 COMPONENTS STATUS

1. ✅ **LiveNarratorComponent** (`live://narrator`) - DONE
   - Continuous stream analysis with TTS output
   - Configurable triggers ("alert on person")
   - Modes: full, diff, track
   - History of descriptions

2. ⏳ **WebPanelComponent** (`web://panel`) - TODO
   - Flask/FastAPI based dashboard
   - WebSocket for live updates
   - Camera grid view

3. ✅ **SmartMonitorComponent** (`smart://monitor`) - DONE
   - Buffered frame capture
   - Adaptive intervals
   - Zone-based monitoring

4. ⏳ **RecorderComponent** (`record://clip`) - TODO
   - Save clips when triggered
   - Configurable pre/post buffer
   - Compression options

5. ✅ **MotionDiffComponent** (`motion://analyze`) - DONE
   - Pixel-level diff detection
   - Region extraction
   - AI analysis on changed regions only

### 📋 RECENT ADDITIONS (2024-11-29)

- `sq watch` - Qualitative parameters (--detect person --sensitivity high)
- `sq live narrator --mode diff` - Describe only changes
- `sq live narrator --mode track --focus person` - Track person
- Email alerts via `send_alert(message, email=True)`
- Presets system (`streamware/presets.py`)


## Completed (2024-11-29)
- [x] Update README.md z PyPI badges i przykładami CLI
- [x] Video captioning z scene detection i object tracking
- [x] Napraw testy automation (xdotool jako primary)
- [x] Wycisz komunikaty o brakujących zależnościach (debug level)
- [x] xdotool jako primary dla automation (zamiast pyautogui)
- [x] Helpful examples gdy brakuje parametru w sq CLI
- [x] Video analysis modes: full, stream, diff
- [x] StreamComponent dla real-time stream analysis (RTSP, HLS, YouTube, Twitch, screen, webcam)
- [x] sq stream command z obsługą różnych źródeł
- [x] Screen monitor i continuous watching
- [x] Przykłady: stream_analysis.py, screen_monitor.py
- [x] NetworkScanComponent - skanowanie sieci (nmap, arp-scan)
- [x] sq network scan/find/identify/ports
- [x] LLM-powered device queries (find "raspberry pi", "cameras", etc.)
- [x] Przykłady: network_discovery.py, camera_finder.py

tworz odpowiedzi w formie ascii table, JSON lub YAML, yaml domyslnie

WYkrywanie typow urzadzen  Unknown Device
sprawdzaj po tym jakie uzywaja porty, jakie maja uslugi po ptym mozna dokladniej zwalidowac co co tza tym purzadzenia, dodatkowo grupuj urzadzenia wedle fgrupyy i generuj wybrany format

 sq network scan 
============================================================
NETWORK SCAN: 192.168.188.0/24
============================================================
Total devices: 6
------------------------------------------------------------

📡 192.168.188.1
   Hostname: _gateway
   MAC: 68:1D:EF:30:74:48
   Type: Router / Access Point

❓ 192.168.188.142
   Hostname: N/A
   MAC: 28:87:BA:0D:31:D6
   Type: Unknown Device

❓ 192.168.188.146
   Hostname: N/A
   MAC: EC:71:DB:F8:9F:FB
   Type: Unknown Device

🖨️ 192.168.188.158
   Hostname: N/A
   MAC: 3C:2A:F4:E8:C6:F8
   Type: Network Printer

❓ 192.168.188.176
   Hostname: N/A
   MAC: E8:A0:ED:55:B9:79
   Type: Unknown Device

❓ 192.168.188.212
   Hostname: nvidia
   MAC: N/A
   Type: Unknown Device

------------------------------------------------------------
By type:
  📡 router: 1
  ❓ unknown: 4
  🖨️ printer: 1