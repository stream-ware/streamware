# Voice Shell - Browser-based Voice Interface

Real-time voice chat with Streamware using WebSocket and browser audio.

## Quick Start

```bash
# Start voice shell server
sq voice-shell

# Or with custom port
sq voice-shell --port 9000

# Open in browser
# http://localhost:8766
```

## Features

### 🎤 Voice Input (Browser STT)
- Click microphone button or press **Space** to talk
- Uses Web Speech API (Chrome, Edge, Safari)
- Supports voice commands in English

### 🔊 Voice Output (Browser TTS)
- Automatic text-to-speech responses
- Uses Web Speech API
- Configurable voice and rate

### 🖥️ Shell Output Streaming
- Real-time command output in browser
- Color-coded messages (input, command, error, TTS)
- Command history

### 📡 Event-Driven Architecture
- WebSocket for real-time communication
- Simple event sourcing pattern
- Events: `voice_input`, `command_parsed`, `command_executed`, `tts_speak`, etc.

## Browser Interface

```
+------------------------------------------+
|        🎤 Streamware Voice Shell         |
|  [●] Connected    [●] Voice Ready        |
+------------------------------------------+
|                    |                     |
|  🖥️ Shell Output    |  🎤 Voice Control   |
|                    |                     |
|  > detect person   |      [🎤]           |
|  ✅ Start person    |   Click to talk     |
|     detection...   |                     |
|  $ sq watch ...    |  [____________]     |
|  🎯 Watch: detect  |   Type command      |
|                    |                     |
|                    |  [✓ Yes] [✗ No]     |
|                    |  [⏹ Stop]           |
|                    |                     |
|                    |  📹 URL: rtsp://... |
|                    |  📧 Email: (not set)|
+------------------------------------------+
```

## Voice Commands

### Detection
```
"detect person"
"track cars for 10 minutes"
"count people and email me"
```

### Confirmation
```
"yes" / "execute" / "okay"  → Confirm command
"no" / "cancel"             → Cancel command
```

### Control
```
"stop"      → Stop running process
"help"      → Show help
"context"   → Show current settings
```

## Architecture

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│   Browser UI    │◄──────────────────►│  VoiceShellServer│
│                 │                    │                  │
│  ┌───────────┐  │                    │  ┌────────────┐  │
│  │ Web Speech│  │   voice_input      │  │  LLMShell  │  │
│  │    API    │──┼───────────────────►│  │            │  │
│  │  (STT)    │  │                    │  │  ┌──────┐  │  │
│  └───────────┘  │                    │  │  │ LLM  │  │  │
│                 │   command_parsed   │  │  │Parser│  │  │
│  ┌───────────┐  │◄───────────────────┼──┤  └──────┘  │  │
│  │ Web Speech│  │                    │  │            │  │
│  │    API    │  │   tts_speak        │  │  ┌──────┐  │  │
│  │  (TTS)    │◄─┼────────────────────┼──┤  │Execut│  │  │
│  └───────────┘  │                    │  │  │ or   │  │  │
│                 │   command_output   │  │  └──────┘  │  │
│  ┌───────────┐  │◄───────────────────┼──┤            │  │
│  │  Output   │  │                    │  └────────────┘  │
│  │  Panel    │  │                    │                  │
│  └───────────┘  │                    │  ┌────────────┐  │
│                 │                    │  │ EventStore │  │
└─────────────────┘                    │  │  (Events)  │  │
                                       │  └────────────┘  │
                                       └──────────────────┘
```

## Event Types

| Event | Direction | Description |
|-------|-----------|-------------|
| `voice_input` | Client→Server | Voice transcription from browser |
| `text_input` | Client→Server | Text input from form |
| `confirm` | Client→Server | Confirm pending command |
| `cancel` | Client→Server | Cancel pending command |
| `stop` | Client→Server | Stop running process |
| `command_parsed` | Server→Client | LLM parsing result |
| `command_executed` | Server→Client | Command started |
| `command_output` | Server→Client | Command stdout line |
| `command_error` | Server→Client | Error occurred |
| `command_completed` | Server→Client | Command finished |
| `tts_speak` | Server→Client | Text for TTS |
| `context_updated` | Server→Client | Session context |

## Configuration

### Environment Variables

```bash
# Default video source
SQ_DEFAULT_URL=rtsp://admin:pass@192.168.1.100:554/stream

# LLM settings
SQ_OLLAMA_URL=http://localhost:11434
SQ_MODEL=llama3.2
```

### CLI Options

```bash
sq voice-shell --help

  --host HOST       Host to bind (default: 0.0.0.0)
  --port PORT       WebSocket port (default: 8765)
  --model MODEL     LLM model (default: llama3.2)
```

## Browser Compatibility

| Browser | STT | TTS | WebSocket |
|---------|-----|-----|-----------|
| Chrome | ✅ | ✅ | ✅ |
| Edge | ✅ | ✅ | ✅ |
| Safari | ✅ | ✅ | ✅ |
| Firefox | ❌ | ✅ | ✅ |

Note: Firefox doesn't support Web Speech API for STT. Use text input instead.

## Example Session

```
# Start server
$ sq voice-shell
🎤 Voice Shell Server starting...
   WebSocket: ws://0.0.0.0:8765
   HTTP UI: http://localhost:8766
   Model: llama3.2

✅ Server running. Open http://localhost:8766 in browser
   Press Ctrl+C to stop

# In browser:
[User clicks 🎤 and says: "detect person and email me when found"]

> detect person and email me when found
✅ Start person detection, send email notification
   Command: sq watch --detect person --email user@example.com --notify-mode instant
🔊 Start person detection, send email notification. Say yes to execute.

[User says: "yes"]

$ sq watch --url rtsp://... --detect person --email user@example.com
🎯 Watch: detect person
   📧 Email: user@example.com
```

## Troubleshooting

### Voice not working
- Check browser permissions for microphone
- Try Chrome or Edge (best STT support)
- Click the microphone button to start

### WebSocket connection failed
- Check if server is running
- Check firewall settings
- Try different port: `sq voice-shell --port 9000`

### Commands not executing
- Check Ollama is running: `ollama serve`
- Check model is available: `ollama list`
- View server logs for errors

## Related

- [LLM Shell](LLM_SHELL.md) - Terminal-based shell
- [Function Registry](../streamware/function_registry.py) - Available functions
- [Voice Automation Guide](v2/guides/VOICE_AUTOMATION_GUIDE.md) - TTS/STT setup
