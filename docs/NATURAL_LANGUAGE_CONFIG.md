# Streamware - Natural Language Configuration

## Overview

Streamware supports **natural language configuration** - describe what you want in plain Polish or English, and the system will configure itself automatically.

## Quick Start

```bash
# Track people
sq watch "śledź osoby"
sq watch "track person"

# Get alerts
sq watch "powiadom gdy ktoś wchodzi"
sq watch "tell me when someone enters"

# Describe scene
sq watch "opisz co się dzieje"
sq watch "describe what's happening"

# Count objects
sq watch "ile osób w pokoju"
sq watch "count people"
```

## Supported Commands

### Actions (What to do)

| Action | Polish | English |
|--------|--------|---------|
| **Track** | śledź, obserwuj | track, watch, follow |
| **Count** | ile, policz, liczba | count, how many |
| **Describe** | opisz, co się dzieje | describe, what is happening |
| **Alert** | powiadom, alarm | alert, notify, warn |
| **Detect** | wykryj, znajdź | detect, find, spot |

### Targets (What to look for)

| Target | Polish | English |
|--------|--------|---------|
| **Person** | osoba, ludzie, ktoś | person, people, someone |
| **Car** | samochód, auto, pojazd | car, vehicle, auto |
| **Cat** | kot | cat, kitty |
| **Dog** | pies | dog, doggy |
| **Bird** | ptak | bird |
| **Animal** | zwierzę, zwierzak | animal, pet |
| **Motion** | ruch | motion, movement |

### Events (When)

| Event | Polish | English |
|-------|--------|---------|
| **Enter** | wchodzi, wejście, pojawia | enters, entering |
| **Leave** | wychodzi, znika, opuszcza | leaves, exits |
| **Move** | porusza, rusza | moves, moving |
| **Approach** | zbliża, nadchodzi | approaches |

### Speed Modifiers

| Speed | Polish | English | FPS |
|-------|--------|---------|-----|
| **Realtime** | natychmiast, w czasie rzeczywistym | realtime, instant | 5.0 |
| **Fast** | szybko, szybki | fast, quick | 2.0 |
| **Normal** | (default) | (default) | 1.0 |
| **Slow** | wolno, szczegółowo, dokładnie | slow, detailed | 0.5 |

## Examples

### Basic Tracking

```bash
# Polish
sq watch "śledź osoby"
sq watch "obserwuj kota"
sq watch "śledź samochody"

# English
sq watch "track person"
sq watch "watch for dogs"
sq watch "follow cars"
```

### Alerts

```bash
# Polish
sq watch "powiadom gdy ktoś wchodzi"
sq watch "alarm gdy zbliża się samochód"
sq watch "ostrzeż gdy pies wyjdzie"

# English
sq watch "alert when someone enters"
sq watch "notify when car approaches"
sq watch "warn when dog leaves"
```

### Counting

```bash
# Polish
sq watch "ile osób w pokoju"
sq watch "policz samochody"
sq watch "liczba kotów"

# English
sq watch "count people"
sq watch "how many cars"
sq watch "count animals"
```

### Descriptions (with LLM)

```bash
# Polish
sq watch "opisz co się dzieje"
sq watch "szczegółowo opisz scenę"

# English
sq watch "describe what's happening"
sq watch "detailed analysis"
```

### Speed Control

```bash
# Fast detection (2 FPS)
sq watch "szybko wykrywaj osoby"
sq watch "fast track person"

# Realtime (5 FPS)
sq watch "śledź w czasie rzeczywistym"
sq watch "realtime detection"

# Slow/detailed (0.5 FPS + LLM)
sq watch "wolno i szczegółowo"
sq watch "slow detailed analysis"
```

## Configuration Mapping

Natural language is converted to configuration:

| Command | FPS | Mode | LLM | TTS |
|---------|-----|------|-----|-----|
| "track person" | 1.0 | track | ❌ | ✅ |
| "describe scene" | 0.2 | full | ✅ | ✅ |
| "count people" | 1.0 | track | ❌ | ✅ |
| "fast detection" | 2.0 | track | ❌ | ✅ |
| "slow detailed" | 0.5 | full | ✅ | ✅ |
| "alert on enter" | 1.0 | track | ❌ | ✅ |

## API Usage

```python
from streamware.intent import parse_intent, apply_intent

# Parse natural language
intent = parse_intent("śledź osoby wchodzące")

# Check parsed values
print(intent.action)   # "track"
print(intent.target)   # "person"
print(intent.trigger)  # "enter"
print(intent.fps)      # 1.0
print(intent.llm)      # False

# Apply to config
apply_intent(intent)

# Get environment variables
env_vars = intent.to_env()
# {'SQ_STREAM_FPS': '1.0', 'SQ_STREAM_MODE': 'track', ...}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Natural Language Input                                      │
│   "powiadom gdy ktoś wchodzi"                              │
└─────────────────────────────────────────────────────────────┘
                    ↓ parse_intent()
┌─────────────────────────────────────────────────────────────┐
│ Intent Object                                               │
│   action: alert                                             │
│   target: person                                            │
│   trigger: enter                                            │
│   fps: 1.0                                                  │
└─────────────────────────────────────────────────────────────┘
                    ↓ to_env()
┌─────────────────────────────────────────────────────────────┐
│ Environment Variables                                       │
│   SQ_STREAM_FPS=1.0                                        │
│   SQ_STREAM_MODE=track                                      │
│   SQ_STREAM_FOCUS=person                                    │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Detection Pipeline                                          │
│   capture → motion → YOLO → track → [LLM] → TTS            │
└─────────────────────────────────────────────────────────────┘
```

## Files

- `streamware/intent.py` - Natural language parser
- `streamware/workflow.py` - YAML workflow support
- `streamware/config.py` - Configuration management
- `workflow.example.yaml` - Example workflow file

## See Also

- [DETECTION_MATRIX.md](../DETECTION_MATRIX.md) - Detection capabilities
- [workflow.example.yaml](../workflow.example.yaml) - YAML workflow format
