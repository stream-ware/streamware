# Natural Language Configuration

Configure Streamware using natural language (Polish or English).

## Quick Start

```bash
# English
sq watch "track person"
sq watch "count cars"
sq watch "describe scene"
sq watch "alert when someone enters"

# Polish
sq watch "śledź osoby"
sq watch "ile samochodów"
sq watch "opisz co się dzieje"
sq watch "powiadom gdy ktoś wchodzi"
```

## Supported Commands

### Actions

| Action | English | Polish |
|--------|---------|--------|
| Track | track, watch, follow | śledź, obserwuj |
| Count | count, how many | ile, policz |
| Describe | describe, what is | opisz, co się dzieje |
| Alert | alert, notify | powiadom, alarm |
| Detect | detect, find | wykryj, znajdź |

### Targets

| Target | English | Polish |
|--------|---------|--------|
| Person | person, people | osoba, ludzie |
| Car | car, vehicle | samochód, auto |
| Cat | cat | kot |
| Dog | dog | pies |
| Bird | bird | ptak |
| Animal | animal, pet | zwierzę |

### Events

| Event | English | Polish |
|-------|---------|--------|
| Enter | enters, entering | wchodzi |
| Leave | leaves, exits | wychodzi |
| Move | moves, moving | porusza |
| Approach | approaches | zbliża |

### Speed

| Speed | English | Polish | FPS |
|-------|---------|--------|-----|
| Realtime | realtime, instant | natychmiast | 5.0 |
| Fast | fast, quick | szybko | 2.0 |
| Normal | (default) | (default) | 1.0 |
| Slow | slow, detailed | wolno, szczegółowo | 0.5 |

## Examples

### Basic Tracking
```bash
sq watch "track person"              # Track any person
sq watch "śledź koty"                # Track cats
sq watch "follow cars"               # Follow vehicles
```

### Alerts
```bash
sq watch "alert when someone enters"
sq watch "powiadom gdy ktoś wchodzi"
sq watch "notify when car approaches"
```

### Counting
```bash
sq watch "count people"
sq watch "ile osób w pokoju"
sq watch "how many cars"
```

### Speed Control
```bash
sq watch "fast track person"         # 2 FPS
sq watch "realtime detection"        # 5 FPS
sq watch "slow detailed analysis"    # 0.5 FPS + LLM
```

## How It Works

```
"powiadom gdy ktoś wchodzi"
         ↓
    parse_intent()
         ↓
┌─────────────────────┐
│ Intent:             │
│   action: alert     │
│   target: person    │
│   trigger: enter    │
│   fps: 1.0          │
│   llm: false        │
└─────────────────────┘
         ↓
    to_env()
         ↓
┌─────────────────────┐
│ SQ_STREAM_FPS=1.0   │
│ SQ_STREAM_MODE=track│
│ SQ_STREAM_FOCUS=... │
└─────────────────────┘
```

## Python API

```python
from streamware.intent import parse_intent, apply_intent

# Parse any natural language
intent = parse_intent("śledź osoby wchodzące")

print(intent.action)    # "track"
print(intent.target)    # "person"
print(intent.trigger)   # "enter"
print(intent.fps)       # 1.0
print(intent.llm)       # False
print(intent.describe()) # "Śledzę person przy wejściu (1.0 FPS) tylko YOLO"

# Apply to config
apply_intent(intent)

# Get CLI args
args = intent.to_cli_args()
# ['--mode', 'track', '--focus', 'person', '--tts', '--tts-diff']

# Get env vars
env = intent.to_env()
# {'SQ_STREAM_FPS': '1.0', 'SQ_STREAM_MODE': 'track', ...}
```

## Adding Custom Keywords

Edit `streamware/intent.py`:

```python
INTENT_KEYWORDS = {
    "track": ["track", "follow", "śledź", "obserwuj", 
              "my_custom_word"],  # Add here
    ...
}
```
