# 🎤 Voice Shell Dashboard v2

> Interactive voice-controlled dashboard for video surveillance automation.

## Overview

Voice Shell Dashboard is a browser-based interface that combines:
- **Voice Control** - Speak commands naturally
- **Multi-session** - Run multiple conversations and processes
- **Customizable Grid** - Drag & drop panel layout
- **Multi-language** - EN/PL/DE with full UI translation
- **Real-time Streaming** - Live command output

## Quick Start

```bash
# Start the server
sq voice-shell --port 9000

# Open in browser
http://localhost:9001
```

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎤 Streamware Voice Shell          ● Connected  ○ Ready    [🇬🇧][🇵🇱][🇩🇪] [🔄] │
├─────────┬───────────────────────────┬───────────────────────────────────────┤
│         │                           │                                       │
│ 💬 Conv │   🖥️ Shell Output         │  🎤 Audio         [⋮⋮][⛶]             │
│ [⋮⋮][⛶] │   [📋][🗑️][⋮⋮][⛶]        │  [🎤] Ready                           │
│         │                           │  [⏹][🔄][⚡]                           │
├─────────┤   > track person          ├───────────────────────────────────────┤
│         │   🔊 How would you...     │                                       │
│ ⚙️ Proc │   > 1                     │  💬 Text Input    [⋮⋮][⛶]             │
│ [⋮⋮][⛶] │   🔊 Executing...         │  [👤][📧][⏹][📊]                       │
│         │   🚀 EXECUTING COMMAND    │  [______________][Send]               │
│         │   $ sq live narrator...   │  [Yes][No][New]                       │
├─────────┤   Frame #1...             ├───────────────────────────────────────┤
│         │   Frame #2...             │                                       │
│ [⌟]     │                     [⌟]   │  📊 Variables     [➕][⋮⋮][⛶]         │
│         │                           │  url: rtsp://192.168.1.100            │
│         │                           │  email: tom@sapletta.com              │
│         │                           │  language: [PL ▼]                     │
└─────────┴───────────────────────────┴───────────────────────────────────────┘
```

## Features

### 🎤 Voice Control

| Action | Voice Command |
|--------|---------------|
| Track person | "track person" |
| Track with email | "track person and email" |
| Stop process | "stop" |
| Check status | "status" |
| Confirm | "yes", "okay", "tak" |
| Cancel | "no", "cancel", "nie" |

### 🌐 Multi-language Support

```javascript
// URL parameter
http://localhost:9001/#lang=pl

// Supported languages
EN - English (default)
PL - Polski
DE - Deutsch
```

All UI elements are translated:
- Quick action buttons
- Status messages
- TTS voice prompts
- Confirmation dialogs

### 🎛️ Customizable Grid

**Drag panels:**
1. Click `⋮⋮` button in panel header
2. Drag to new position on 10x7 grid
3. Release to place

**Resize panels:**
1. Click `⌟` in bottom-right corner
2. Drag to resize
3. Release when done

**Reset layout:**
- Click `🔄 Reset` in header

**Grid saved in URL:**
```
http://localhost:9001/#grid=%7B%22output-panel%22%3A%7B%22col%22%3A3...%7D%7D
```

### 💬 Multi-session Support

**Conversations** (idle sessions):
- Start new conversations while processes run
- Full history preserved
- Click to switch

**Processes** (running commands):
- View running processes
- Stop any process
- See output in real-time

### 📊 Variables Panel

Editable variables used in commands:
- `url` - RTSP stream URL
- `email` - Notification email
- `duration` - Detection duration (seconds)
- `focus` - Detection target (person/car/motion)

Variables auto-sync with server via WebSocket.

## URL State Management

Track user activity via URL hash:

```
http://localhost:9001/#lang=pl&panel=output-panel&action=typing&session=s1
```

| Parameter | Description |
|-----------|-------------|
| `lang` | Current language |
| `panel` | Active panel |
| `action` | Current action (typing, speaking, etc.) |
| `session` | Current session ID |
| `grid` | Panel positions (JSON) |

## API Events

### WebSocket Messages (Client → Server)

```javascript
// Voice input
{type: 'voice_input', content: 'track person'}

// Text input
{type: 'text_input', content: 'status'}

// Session management
{type: 'new_session'}
{type: 'switch_session', content: 'session_id'}

// Language change
{type: 'set_language', content: 'pl'}

// Variable change
{type: 'set_variable', content: {key: 'url', value: 'rtsp://...'}}
```

### WebSocket Events (Server → Client)

```javascript
// TTS speak
{type: 'tts_speak', data: {text: 'How would you like...'}}

// Command executed
{type: 'command_executed', data: {command: 'sq live narrator...'}}

// Session events
{type: 'session_created', data: {session: {...}, sessions: [...]}}
{type: 'session_switched', data: {session: {...}, output: [...]}}

// Config loaded
{type: 'config_loaded', data: {language: 'pl', email: '...', url: '...'}}
```

## Integration Examples

### With Home Assistant

```yaml
# configuration.yaml
rest_command:
  start_surveillance:
    url: "http://localhost:9001/api/command"
    method: POST
    payload: '{"command": "track person and email"}'

automation:
  - alias: "Start surveillance on motion"
    trigger:
      platform: state
      entity_id: binary_sensor.motion
      to: 'on'
    action:
      - service: rest_command.start_surveillance
```

### With Node-RED

```json
[
    {
        "id": "websocket-voice-shell",
        "type": "websocket out",
        "url": "ws://localhost:9001/ws",
        "msg": {"type": "text_input", "content": "track person"}
    }
]
```

### With Python Scripts

```python
import asyncio
import websockets
import json

async def send_command(command):
    async with websockets.connect('ws://localhost:9001/ws') as ws:
        await ws.send(json.dumps({
            'type': 'text_input',
            'content': command
        }))
        
        # Listen for response
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"Event: {data['type']}")
            
            if data['type'] == 'command_completed':
                break

asyncio.run(send_command('track person'))
```

### With cURL

```bash
# Send command via HTTP (if API endpoint enabled)
curl -X POST http://localhost:9001/api/command \
  -H "Content-Type: application/json" \
  -d '{"command": "track person", "language": "pl"}'
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Toggle voice recording |
| `Escape` | Close expanded panel |
| `Enter` | Send text input |

## Testing

```bash
# Run all GUI tests
pytest tests/test_voice_shell_gui.py -v
pytest tests/test_voice_shell_gui_e2e.py -v

# Run specific test
pytest tests/test_voice_shell_gui_e2e.py::TestTranslator -v
```

## Troubleshooting

### Microphone not working
- Check browser permissions
- Use HTTPS or localhost
- Chrome/Edge recommended

### No voice output
- Check browser TTS support
- Try different voice in browser settings

### Grid not saving
- Clear URL hash and try again
- Check browser console for errors

## Related Documentation

- [Architecture](../ARCHITECTURE.md) - System design
- [API Reference](../API.md) - Full API documentation
- [Examples](../../examples/) - Usage examples
- [Quick Start](../QUICKSTART.md) - Getting started guide

## License

MIT License - see [LICENSE](../../LICENSE)
