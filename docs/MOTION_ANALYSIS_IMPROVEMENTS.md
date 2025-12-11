# Motion Analysis System - Analiza i Plan Ulepszeń

## 1. Obecna Architektura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  RTSP Camera    │────▶│  FrameDiffAnalyzer│────▶│   FrameDelta    │
│  (live stream)  │     │  (OpenCV)         │     │   (dataclass)   │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌──────────────────┐              │
                        │  DSL Generator   │◀─────────────┘
                        │  (text output)   │
                        └────────┬─────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
    ┌─────────────────┐ ┌───────────────┐ ┌───────────────────┐
    │ motion_player.js│ │ HTML Generator│ │ LLM Analysis      │
    │ (SVG renderer)  │ │ (lightweight) │ │ (is_significant)  │
    └─────────────────┘ └───────────────┘ └───────────────────┘
```

## 2. Co Działa Dobrze ✅

| Komponent | Status | Opis |
|-----------|--------|------|
| Frame capture | ✅ | FastCapture z RAM disk, persistent RTSP |
| Motion detection | ✅ | OpenCV background subtraction + blob detection |
| Blob tracking | ✅ | ID assignment, velocity calculation |
| DSL generation | ✅ | Human-readable format |
| HTML player | ✅ | Lightweight, DSL-driven, 80% mniejszy |
| Background thumbnails | ✅ | 128px captured during analysis |

## 3. Potencjalne Ulepszenia

### 3.1 Struktura Danych DSL

**Problem:** DSL jest verbose i text-based, trudny do parsowania przez LLM.

**Propozycja:** Dodać kompaktowy format JSON obok DSL:

```json
{
  "summary": {
    "duration_s": 20,
    "frames": 4,
    "avg_motion": 27.1,
    "objects_tracked": 5
  },
  "objects": {
    "1": {
      "first_seen": 1, "last_seen": 4,
      "path": "RIGHT→DOWN→LEFT",
      "total_distance": 0.19,
      "classification": "moving_object"
    }
  },
  "timeline": [
    {"frame": 1, "motion": 100.0, "events": ["APPEAR:1"]},
    {"frame": 2, "motion": 2.3, "events": ["MOVE:1:RIGHT", "APPEAR:2,3"]}
  ]
}
```

### 3.2 Klasyfikacja Obiektów

**Problem:** Bloby nie mają semantycznej klasyfikacji (person/vehicle/animal).

**Propozycja:** Dodać lightweight classifier:
- Aspect ratio → person (0.3-0.6), vehicle (1.5-3.0)
- Size pattern → small/medium/large
- Movement pattern → walking/running/stationary

### 3.3 Trajektoria i Predykcja

**Problem:** Brak analizy trajektorii i predykcji ruchu.

**Propozycja:**
- Polynomial trajectory fitting
- Predicted position for next N frames
- Entry/exit zone detection

### 3.4 Agregacja dla LLM

**Problem:** LLM otrzymuje per-frame data, trudno o big picture.

**Propozycja:** Summary block:
```
SCENE_SUMMARY:
  - Primary object moved LEFT-TO-RIGHT across 70% of frame
  - 2 secondary objects appeared mid-scene, stationary
  - Motion pattern suggests: person walking through room
```

### 3.5 Confidence Scoring

**Problem:** Brak confidence dla detekcji i klasyfikacji.

**Propozycja:**
```
BLOB id=1 pos=(0.5,0.5) confidence=0.85 classification=PERSON:0.72
```

## 4. Format Prompt dla LLM

### 4.1 Obecny Format (verbose)
```
FRAME 1 @ 15:53:41.771
  DELTA motion_pct=100.0% regions=1
  BLOB id=1 pos=(0.499,0.499) size=(1.000,1.000) vel=(0.0000,0.0000)
  ...
```

### 4.2 Proponowany Format (compact)
```
MOTION_ANALYSIS v2
Duration: 20s | Frames: 4 | Objects: 5

OBJECTS:
#1: frames=1-4, path=R→D→L, dist=0.19, type=moving
#2: frames=2-4, path=→D→U, dist=0.08, type=moving  
#3: frames=2-4, path=→D→U, dist=0.04, type=moving
#4: frames=4, stationary
#5: frames=4, stationary

TIMELINE:
F1: motion=100%, +obj#1
F2: motion=2%, #1→RIGHT, +obj#2,#3
F3: motion=4%, all↓DOWN
F4: motion=2%, #1-3↑UP, +obj#4,#5

INTERPRETATION:
- Main activity: object traversing scene L→R→center
- Pattern: person entering from left, moving to center
- Confidence: HIGH (consistent tracking, clear trajectory)
```

## 5. Implementacja Priorytetowa

### Faza 1: Quick Wins (1-2h)
1. [ ] Dodać `generate_llm_summary()` do DSL generator
2. [ ] Compact timeline format
3. [ ] Object path summary (direction arrows)

### Faza 2: Medium Effort (4-8h)
4. [ ] JSON export alongside DSL
5. [ ] Basic object classification (aspect ratio)
6. [ ] Trajectory analysis (dominant direction)

### Faza 3: Advanced (1-2 days)
7. [ ] ML-based blob classification
8. [ ] Predictive tracking
9. [ ] Zone-based event detection
10. [ ] Real-time streaming to LLM

## 6. Przykład Użycia z LLM

```python
# Generowanie promptu z danych DSL
prompt = generate_motion_prompt(
    deltas=frame_deltas,
    question="Is there a person in the scene? What are they doing?"
)

# Wysłanie do LLM
response = ollama.generate(
    model="llama3:8b",
    prompt=prompt,
    options={"num_predict": 100}
)
```

## 7. Metryki Sukcesu

| Metryka | Obecna | Cel |
|---------|--------|-----|
| Rozmiar promptu | ~2KB | <500B |
| Czas parsowania LLM | ~2s | <0.5s |
| Accuracy klasyfikacji | N/A | >80% |
| False positive rate | ~30% | <10% |
