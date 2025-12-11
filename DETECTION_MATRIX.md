# Detection Matrix - Streamware Object Detection

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Total Objects** | 140 |
| **Moving Objects** | 84 |
| **YOLO Detectable** | 80 |
| **LLM Only** | 60 |
| **Categories** | 4 (person, animal, vehicle, object) |

## 🔧 Detection Tools

| Tool | Time (ms) | Accuracy | Use Case |
|------|-----------|----------|----------|
| **Motion** | 5 | 55% | Fast motion gate, triggers other detectors |
| **YOLO** | 15 | 92% | 80 COCO classes, best speed/accuracy |
| **ReID** | 25 | 80% | Re-identify same object across frames |
| **HOG** | 50 | 78% | Person detection fallback |
| **LLM Fast** (moondream) | 500 | 82% | Any object, fast inference |
| **LLM Accurate** (llava:7b) | 4000 | 95% | Any object, highest accuracy |

## 🎯 Detection Priority Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ 1. MOTION DETECTION (5ms, 55%)                              │
│    └─ Fast gate - skip frame if no motion                   │
├─────────────────────────────────────────────────────────────┤
│ 2. YOLO (15ms, 92%) ★ TRUSTED SOURCE                        │
│    └─ 80 object classes from COCO dataset                   │
│    └─ If confidence >= 50%, skip LLM entirely               │
│    └─ YOLO result overrides LLM hallucinations              │
├─────────────────────────────────────────────────────────────┤
│ 3. ReID (25ms, 80%)                                         │
│    └─ Track same object across frames                       │
│    └─ Works with person, animal, vehicle                    │
├─────────────────────────────────────────────────────────────┤
│ 4. HOG (50ms, 78%)                                          │
│    └─ Person detection fallback                             │
│    └─ Used when YOLO unavailable                            │
├─────────────────────────────────────────────────────────────┤
│ 5. LLM Fast (500ms, 82%)                                    │
│    └─ moondream model                                       │
│    └─ Only for objects NOT in YOLO classes                  │
│    └─ Validated against YOLO result                         │
├─────────────────────────────────────────────────────────────┤
│ 6. GUARDER VALIDATION                                       │
│    └─ If YOLO=False but Guarder="target present" → IGNORE   │
│    └─ Prevents LLM hallucinations                           │
└─────────────────────────────────────────────────────────────┘
```

## 🛡️ Anti-Hallucination Guard

```python
# YOLO > LLM/Guarder (YOLO is more reliable for known objects)
if not yolo_has_target and guarder_says_target:
    # Guarder is hallucinating - trust YOLO
    result = "No target visible"
```

| Scenario | YOLO | Guarder | Result |
|----------|------|---------|--------|
| Both agree: target | ✅ | ✅ | ✅ Target detected |
| Both agree: no target | ❌ | ❌ | ❌ No target |
| YOLO yes, Guarder no | ✅ | ❌ | ✅ Trust YOLO |
| **YOLO no, Guarder yes** | ❌ | ✅ | ❌ **Hallucination blocked** |

## 🐾 Moving Objects by Category

### Person (Priority 1)
| Object | YOLO | HOG | ReID | Best Tool | Time |
|--------|------|-----|------|-----------|------|
| person | ✅ | ✅ | ✅ | YOLO | 15ms |

### Animals (Priority 2) - 51 objects

#### YOLO Detectable (11)
| Object | YOLO | ReID | Time |
|--------|------|------|------|
| bird | ✅ | ✅ | 15ms |
| cat | ✅ | ✅ | 15ms |
| dog | ✅ | ✅ | 15ms |
| horse | ✅ | ✅ | 15ms |
| sheep | ✅ | ✅ | 15ms |
| cow | ✅ | ✅ | 15ms |
| elephant | ✅ | ✅ | 15ms |
| bear | ✅ | ✅ | 15ms |
| zebra | ✅ | ✅ | 15ms |
| giraffe | ✅ | ✅ | 15ms |
| teddy bear | ✅ | ✅ | 15ms |

#### LLM Only (40)
| Object | ReID | Time |
|--------|------|------|
| squirrel | ✅ | 500ms |
| rabbit | ✅ | 500ms |
| deer | ✅ | 500ms |
| fox | ✅ | 500ms |
| raccoon | ✅ | 500ms |
| crow | ✅ | 500ms |
| pigeon | ✅ | 500ms |
| sparrow | ✅ | 500ms |
| butterfly | ✅ | 500ms |
| bee | ✅ | 500ms |
| snake | ✅ | 500ms |
| lizard | ✅ | 500ms |
| frog | ✅ | 500ms |
| fish | ✅ | 500ms |
| hamster | ✅ | 500ms |
| parrot | ✅ | 500ms |
| ... and 24 more |

### Vehicles (Priority 3) - 32 objects

#### YOLO Detectable (12)
| Object | YOLO | ReID | Time |
|--------|------|------|------|
| bicycle | ✅ | ✅ | 15ms |
| car | ✅ | ✅ | 15ms |
| motorcycle | ✅ | ✅ | 15ms |
| airplane | ✅ | ✅ | 15ms |
| bus | ✅ | ✅ | 15ms |
| train | ✅ | ✅ | 15ms |
| truck | ✅ | ✅ | 15ms |
| boat | ✅ | ✅ | 15ms |
| skateboard | ✅ | ✅ | 15ms |
| surfboard | ✅ | ✅ | 15ms |
| skis | ✅ | ✅ | 15ms |
| snowboard | ✅ | ✅ | 15ms |

#### LLM Only (20)
| Object | ReID | Time |
|--------|------|------|
| drone | ✅ | 500ms |
| scooter | ✅ | 500ms |
| wheelchair | ✅ | 500ms |
| stroller | ✅ | 500ms |
| forklift | ✅ | 500ms |
| tractor | ✅ | 500ms |
| ambulance | ✅ | 500ms |
| police car | ✅ | 500ms |
| fire truck | ✅ | 500ms |
| golf cart | ✅ | 500ms |
| ATV | ✅ | 500ms |
| jet ski | ✅ | 500ms |
| kayak | ✅ | 500ms |
| ... and 7 more |

### Static Objects (Priority 4) - 56 objects
All detectable by YOLO (15ms, 92%)

Examples: bottle, cup, chair, couch, bed, tv, laptop, phone, etc.

## 📈 Performance Matrix

### Speed vs Accuracy Trade-off

```
Accuracy
  95% │                                    ★ LLM Accurate
  92% │            ★ YOLO
  85% │
  82% │                        ★ LLM Fast
  80% │                ★ ReID
  78% │        ★ HOG
  55% │★ Motion
      └───────────────────────────────────────────► Time (ms)
        5    15   25   50        500           4000
```

### Recommended Configuration

| Mode | Config | FPS | Use Case |
|------|--------|-----|----------|
| **DSL Only** | Motion + YOLO only | 50-100+ | Pure tracking, no descriptions |
| **Ultra Fast** | YOLO + skip LLM@0.3 | 5-10 | High-traffic monitoring |
| **Fast** | YOLO + moondream | 1-2 | Standard surveillance |
| **Balanced** | YOLO + llava:7b | 0.3-0.5 | Detailed detection |
| **Accurate** | YOLO + llava:7b + guarder | 0.1-0.2 | High accuracy needed |

### .env Settings for Each Mode

```bash
# DSL Only (fastest - no LLM)
sq live narrator --url "..." --dsl-only --fps 10

# Ultra Fast (~5-10 FPS)
SQ_YOLO_SKIP_LLM_THRESHOLD=0.3
SQ_USE_GUARDER=false
SQ_MODEL=moondream

# Fast (~1-2 FPS)
SQ_YOLO_SKIP_LLM_THRESHOLD=0.5
SQ_USE_GUARDER=false
SQ_MODEL=moondream

# Balanced (~0.3-0.5 FPS)
SQ_YOLO_SKIP_LLM_THRESHOLD=0.5
SQ_USE_GUARDER=false
SQ_MODEL=llava:7b

# Accurate (~0.1-0.2 FPS)
SQ_YOLO_SKIP_LLM_THRESHOLD=1.0  # Always use LLM
SQ_USE_GUARDER=true
SQ_MODEL=llava:7b
```

### LLM Call Decision Tree

```
Frame captured
    │
    ▼
Motion detected? ──NO──► SKIP (5ms)
    │
   YES
    ▼
YOLO detects target? ──YES──► confidence >= threshold?
    │                              │
   NO                            YES ──► SKIP LLM, use YOLO (15ms)
    │                              │
    ▼                            NO
HOG detects person? ──YES──┐      │
    │                      │      ▼
   NO                      └──► CALL LLM (500-4000ms)
    │
    ▼
SKIP - no target (50ms)
```

## 🎮 Available Modes

| Mode | LLM | FPS | Use Case |
|------|-----|-----|----------|
| **track** | ❌ YOLO | ~2.0 | Fast object tracking with movement |
| **fast** | ❌ YOLO | ~5.0 | Maximum speed, minimal processing |
| **count** | ❌ YOLO | ~1.0 | Count objects in frame |
| **security** | ✅ llava | ~1.0 | Intrusion alerts with verification |
| **activity** | ✅ llava | ~0.5 | Describe what people are doing |
| **describe** | ✅ llava | ~0.2 | Detailed scene descriptions |
| **patrol** | ✅ llava | ~0.1 | Periodic monitoring |
| **accurate** | ✅ llava | ~0.2 | Maximum accuracy with LLM |

### Mode Examples:

```bash
# Fast tracking (no LLM)
sq live narrator --url $URL --mode track --focus person --tts

# Security with LLM verification
sq live narrator --url $URL --mode security --tts --trigger "person,vehicle"

# Activity description
sq live narrator --url $URL --mode activity --focus person --tts

# Maximum speed
sq live narrator --url $URL --mode fast --focus person
```

### Mode Configuration:

| Mode | YOLO Skip | Guarder | Interval | Model |
|------|-----------|---------|----------|-------|
| track | 0.3 | ❌ | 1.0s | - |
| fast | 0.0 | ❌ | 0.5s | - |
| count | 0.2 | ❌ | 2.0s | - |
| security | 0.7 | ✅ | 2.0s | llava:7b |
| activity | 0.8 | ✅ | 3.0s | llava:7b |
| describe | 1.0 | ✅ | 5.0s | llava:7b |
| patrol | 0.5 | ✅ | 10.0s | llava:7b |
| accurate | 1.0 | ✅ | 5.0s | llava:7b |

## 📁 Files

- `detection_matrix.csv` - Full matrix with all 140 objects
- `DETECTION_MATRIX.md` - This documentation

## 🔗 See Also

- [ByteTrack](streamware/bytetrack.py) - Multi-object tracking with ReID
- [SmartDetector](streamware/smart_detector.py) - Detection pipeline
- [YOLODetector](streamware/yolo_detector.py) - YOLO wrapper
- [AnimalDetector](streamware/animal_detector.py) - Specialized animal detection
