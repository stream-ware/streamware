# Streamware - Project Analysis & Optimization Guide

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| Total Python files | 93 |
| Total lines of code | 51,836 |
| Large files (>500 lines) | 35 |
| Critical files (>2000 lines) | 3 |

## 📁 Architecture Overview

```
streamware/
├── core/                    # Core framework
│   ├── config.py           # Configuration management (680 lines)
│   ├── core.py             # DSL engine (318 lines)
│   └── intent.py           # Natural language parser (364 lines)
│
├── detection/              # Object detection
│   ├── smart_detector.py   # Detection pipeline (815 lines)
│   ├── yolo_detector.py    # YOLO wrapper (584 lines)
│   └── bytetrack.py        # Object tracking (778 lines)
│
├── processing/             # Frame processing
│   ├── frame_optimizer.py  # Adaptive intervals (506 lines)
│   ├── image_optimizer.py  # Image optimization
│   └── motion_diff.py      # Motion detection (649 lines)
│
├── components/             # Main components
│   ├── live_narrator.py    # 🔴 CRITICAL: 2981 lines
│   ├── network_scan.py     # Network scanning (1001 lines)
│   └── smart_monitor.py    # Smart monitoring (716 lines)
│
├── output/                 # Output handlers
│   ├── response_filter.py  # LLM filtering (1291 lines)
│   └── tts_engine.py       # Text-to-speech
│
└── cli/                    # Command line
    ├── quick_cli.py        # 🔴 CRITICAL: 3554 lines
    └── cli.py              # CLI commands (586 lines)
```

## 🔴 Critical Files - Refactoring Priority

### 1. `live_narrator.py` (2981 lines, 50 functions, 5 classes)

**Problem**: God class doing too many things
- Frame capture
- Detection
- Tracking  
- LLM calls
- TTS output
- HTML generation
- YAML logging

**Proposed Split**:

```
live_narrator.py (2981 lines)
    ↓ refactor to
├── narrator/
│   ├── __init__.py
│   ├── capture.py          # Frame capture (200 lines)
│   ├── detector.py         # Detection wrapper (300 lines)
│   ├── tracker.py          # Object tracking (300 lines)
│   ├── describer.py        # LLM descriptions (400 lines)
│   ├── output.py           # TTS + logging (300 lines)
│   ├── html_generator.py   # HTML reports (400 lines)
│   └── orchestrator.py     # Main loop (500 lines)
```

### 2. `quick_cli.py` (3554 lines)

**Problem**: All CLI commands in one file

**Proposed Split**:

```
quick_cli.py (3554 lines)
    ↓ refactor to
├── cli/
│   ├── __init__.py
│   ├── commands/
│   │   ├── live.py         # Live commands
│   │   ├── watch.py        # Watch commands
│   │   ├── analyze.py      # Analyze commands
│   │   └── config.py       # Config commands
│   └── utils.py            # CLI utilities
```

## 🟡 Optimization Opportunities

### 1. Configuration Simplification

**Current**: 50+ environment variables
```env
SQ_STREAM_FPS=1.0
SQ_STREAM_INTERVAL=1.0
SQ_CAPTURE_FPS=2.0
SQ_MIN_INTERVAL=0.5
SQ_MAX_INTERVAL=1.0
SQ_BASE_INTERVAL=1.0
...
```

**Optimized**: Natural language + presets
```bash
# Instead of 10 env vars:
sq watch "track person fast"

# Or preset:
sq watch --preset track_person
```

### 2. Detection Pipeline

**Current Flow** (redundant checks):
```
frame → motion → YOLO → HOG → LLM → guarder → TTS
         ↓        ↓      ↓
      (check)  (check) (check)  # Multiple redundant checks
```

**Optimized Flow**:
```
frame → smart_detect → [LLM if needed] → output
            ↓
    (single decision point)
```

### 3. Memory Management

**Current**: Frames stored temporarily
```python
# Multiple copies of same frame
frame_path = save_frame(frame)
optimized_path = optimize(frame_path)
thumbnail = create_thumbnail(frame_path)
```

**Optimized**: Single frame reference
```python
class FrameContext:
    raw: np.ndarray
    optimized: Optional[bytes] = None
    thumbnail: Optional[bytes] = None
    
    def get_optimized(self):
        if not self.optimized:
            self.optimized = optimize(self.raw)
        return self.optimized
```

## 📈 Performance Improvements

### Before Optimization

| Step | Time | Notes |
|------|------|-------|
| Capture | 5ms | OK |
| Motion | 5ms | OK |
| YOLO | 50ms | OK |
| HOG | 50ms | Redundant if YOLO works |
| LLM | 4000ms | Often unnecessary |
| Guarder | 3000ms | Often unnecessary |
| **Total** | **7110ms** | 0.14 FPS |

### After Optimization

| Step | Time | Notes |
|------|------|-------|
| Capture | 5ms | OK |
| Motion | 2ms | Optimized |
| YOLO | 15ms | Skip if no motion |
| LLM | 0ms | Skipped (YOLO confident) |
| **Total** | **22ms** | 45 FPS theoretical |

### Key Optimizations Made

1. **FPS-based intervals** - All intervals calculated from single `SQ_STREAM_FPS`
2. **YOLO skip LLM** - Skip LLM when YOLO confidence >= 0.3
3. **Motion gating** - Skip detection if no motion
4. **Guarder disabled** - Not needed for simple tracking
5. **LLM caching** - Cache descriptions per track_id

## 🛠️ Refactoring Example

### Before (live_narrator.py:1500-1600)

```python
# 100 lines of mixed concerns
def _run_narrator(self):
    # Frame capture
    frame = self._capture_frame()
    
    # Detection
    if self.use_smart_detect:
        detection = self._smart_detect(frame)
    else:
        detection = self._simple_detect(frame)
    
    # Tracking
    if self.mode == "track":
        tracking = self._track_objects(detection)
    
    # LLM
    if detection.should_process_llm:
        description = self._call_llm(frame)
    
    # TTS
    if self.tts_enabled:
        self._speak(description)
    
    # Logging
    self._log_entry(detection, description)
    
    # HTML
    self._update_html(frame, detection)
```

### After (using composition)

```python
# orchestrator.py - clean orchestration
class NarratorOrchestrator:
    def __init__(self, config: NarratorConfig):
        self.capture = FrameCapture(config)
        self.detector = SmartDetector(config)
        self.tracker = ObjectTracker(config)
        self.describer = Describer(config)
        self.output = OutputHandler(config)
    
    def run_frame(self) -> FrameResult:
        frame = self.capture.get_frame()
        detection = self.detector.detect(frame)
        
        if detection.has_target:
            tracking = self.tracker.track(detection)
            description = self.describer.describe(frame, tracking)
        else:
            description = "No target"
        
        self.output.emit(frame, detection, description)
        return FrameResult(frame, detection, description)
```

## 📋 Refactoring Checklist

- [ ] Split `live_narrator.py` into modules
- [ ] Split `quick_cli.py` into command modules
- [ ] Create `FrameContext` for memory management
- [ ] Unify configuration through `intent.py`
- [ ] Remove redundant detection steps
- [ ] Add unit tests for each module
- [ ] Document public APIs

## 📚 Documentation Structure

```
docs/
├── README.md                    # Quick start
├── NATURAL_LANGUAGE_CONFIG.md   # Intent-based config ✅
├── PROJECT_ANALYSIS.md          # This file ✅
├── DETECTION_MATRIX.md          # Detection capabilities ✅
├── API/
│   ├── intent.md               # Intent API
│   ├── workflow.md             # Workflow API
│   └── config.md               # Config API
└── EXAMPLES/
    ├── track_person.md
    ├── security_monitor.md
    └── scene_description.md
```

## 🔗 Related Files

- [NATURAL_LANGUAGE_CONFIG.md](NATURAL_LANGUAGE_CONFIG.md) - Natural language interface
- [DETECTION_MATRIX.md](../DETECTION_MATRIX.md) - Detection capabilities
- [workflow.example.yaml](../workflow.example.yaml) - Workflow examples
