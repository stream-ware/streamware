# Live Narrator - Analiza Optymalizacji

## Obecna Architektura

```
┌─────────────────────────────────────────────────────────────────┐
│                     LIVE NARRATOR PIPELINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  RTSP Stream                                                    │
│      │                                                          │
│      ▼                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ FastCapture │───▶│ Smart       │───▶│ Frame       │         │
│  │ (OpenCV/    │    │ Detector    │    │ Optimizer   │         │
│  │  FFmpeg)    │    │ (YOLO+HOG)  │    │ (resize,    │         │
│  │  ~0-5ms     │    │  ~40-700ms  │    │  compress)  │         │
│  └─────────────┘    └─────────────┘    │  ~50ms      │         │
│                            │           └─────────────┘         │
│                            │                  │                 │
│                            ▼                  ▼                 │
│                     ┌─────────────┐    ┌─────────────┐         │
│                     │ Skip if     │    │ Vision LLM  │         │
│                     │ no motion   │    │ (llava:7b)  │         │
│                     │ or no target│    │ ~1.5-3s     │         │
│                     └─────────────┘    └─────────────┘         │
│                                               │                 │
│                                               ▼                 │
│                                        ┌─────────────┐         │
│                                        │ Guarder LLM │         │
│                                        │ (gemma:2b)  │         │
│                                        │ ~200-500ms  │         │
│                                        └─────────────┘         │
│                                               │                 │
│                                               ▼                 │
│                                        ┌─────────────┐         │
│                                        │ TTS Output  │         │
│                                        │ (pyttsx3)   │         │
│                                        └─────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Obecne Czasy (benchmark)

| Component | Czas | Status |
|-----------|------|--------|
| FastCapture | 0-5ms | ✅ Optimal |
| YOLO Detection | 10-50ms (GPU) | ✅ Optimal |
| Smart Detect (HOG fallback) | 700ms | ⚠️ Wolne |
| Frame Optimize | 50ms | ✅ OK |
| Vision LLM (llava:7b) | 1.5-3s | ⚠️ Bottleneck |
| Guarder LLM (gemma:2b) | 200-500ms | ✅ OK |
| **Total Cycle** | **2-4s** | - |

## Propozycje Optymalizacji

### 1. 🚀 Batch Processing (Grupowanie klatek)

**Problem**: Każda klatka analizowana osobno przez LLM.

**Rozwiązanie**: Grupuj 3-5 klatek i analizuj razem.

```python
class BatchFrameAnalyzer:
    def __init__(self, batch_size=3):
        self.batch_size = batch_size
        self.frame_buffer = []
    
    def add_frame(self, frame_path):
        self.frame_buffer.append(frame_path)
        if len(self.frame_buffer) >= self.batch_size:
            return self._analyze_batch()
        return None
    
    def _analyze_batch(self):
        # Stwórz grid 3 klatek w jednym obrazie
        # LLM analizuje wszystkie naraz
        grid = self._create_grid(self.frame_buffer)
        prompt = "Analyze these 3 consecutive frames. Describe any movement or changes."
        result = llm.analyze(grid, prompt)
        self.frame_buffer.clear()
        return result
```

**Korzyści**:
- 3x mniej wywołań LLM
- Lepsze wykrywanie ruchu (kontekst)
- ~1s na 3 klatki zamiast ~3s

---

### 2. 🎯 Hierarchiczne Przetwarzanie

**Problem**: Każda klatka przechodzi pełny pipeline.

**Rozwiązanie**: 3-poziomowa hierarchia:

```
Level 1: YOLO Only (10ms)
    ├── No detection → Skip
    └── Detection → Level 2

Level 2: Fast LLM (moondream, 300ms)
    ├── Low confidence → Level 3
    └── High confidence → Output

Level 3: Accurate LLM (llava:7b, 1.5s)
    └── Final analysis
```

```python
class HierarchicalAnalyzer:
    def analyze(self, frame):
        # Level 1: YOLO
        detections = self.yolo.detect(frame)
        if not detections:
            return None
        
        # Level 2: Fast check
        fast_result = self.fast_llm.analyze(frame)
        if self._is_confident(fast_result):
            return fast_result
        
        # Level 3: Accurate analysis
        return self.accurate_llm.analyze(frame)
```

---

### 3. 📊 Keyframe Extraction (Ekstrakcja kluczowych klatek)

**Problem**: Analizujemy co N sekund, nawet jeśli nic się nie zmieniło.

**Rozwiązanie**: Wykrywaj "keyframes" na podstawie zmian:

```python
class KeyframeExtractor:
    def __init__(self, threshold=0.15):
        self.threshold = threshold
        self.last_keyframe = None
        self.last_histogram = None
    
    def is_keyframe(self, frame):
        histogram = cv2.calcHist([frame], [0,1,2], None, [8,8,8], [0,256,0,256,0,256])
        
        if self.last_histogram is None:
            self.last_histogram = histogram
            return True
        
        # Compare histograms
        diff = cv2.compareHist(self.last_histogram, histogram, cv2.HISTCMP_BHATTACHARYYA)
        
        if diff > self.threshold:
            self.last_histogram = histogram
            return True
        
        return False
```

---

### 4. 🔄 Async Pipeline (Równoległe przetwarzanie)

**Problem**: Sekwencyjne przetwarzanie blokuje capture.

**Rozwiązanie**: Oddzielne wątki dla każdego etapu:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncPipeline:
    def __init__(self):
        self.capture_queue = asyncio.Queue(maxsize=5)
        self.analysis_queue = asyncio.Queue(maxsize=3)
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def capture_loop(self):
        while True:
            frame = await self._capture_frame()
            await self.capture_queue.put(frame)
    
    async def detection_loop(self):
        while True:
            frame = await self.capture_queue.get()
            if self._has_motion(frame):
                await self.analysis_queue.put(frame)
    
    async def analysis_loop(self):
        while True:
            frame = await self.analysis_queue.get()
            # Run LLM in thread pool (non-blocking)
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, self._analyze_with_llm, frame
            )
            self._output(result)
```

---

### 5. 🗜️ Smart Compression (Inteligentna kompresja)

**Problem**: Wysyłamy pełne obrazy do LLM.

**Rozwiązanie**: Kompresuj tylko interesujące regiony:

```python
class SmartCompressor:
    def compress_for_llm(self, frame, detections):
        if not detections:
            # No detections - send thumbnail
            return cv2.resize(frame, (256, 256))
        
        # Crop to detection region with padding
        x, y, w, h = self._get_bounding_box(detections)
        padding = 50
        crop = frame[
            max(0, y-padding):min(frame.shape[0], y+h+padding),
            max(0, x-padding):min(frame.shape[1], x+w+padding)
        ]
        
        # Resize to optimal size for LLM
        return cv2.resize(crop, (384, 384))
```

---

### 6. 📝 Response Caching (Cache odpowiedzi)

**Problem**: Te same sceny analizowane wielokrotnie.

**Rozwiązanie**: Cache na podstawie visual hash:

```python
import imagehash
from PIL import Image

class ResponseCache:
    def __init__(self, ttl=30):
        self.cache = {}
        self.ttl = ttl
    
    def get_or_analyze(self, frame_path, analyzer):
        # Compute perceptual hash
        img = Image.open(frame_path)
        phash = str(imagehash.phash(img))
        
        # Check cache
        if phash in self.cache:
            entry = self.cache[phash]
            if time.time() - entry['time'] < self.ttl:
                return entry['response']
        
        # Analyze and cache
        response = analyzer(frame_path)
        self.cache[phash] = {'response': response, 'time': time.time()}
        return response
```

---

### 7. 🎬 Scene Segmentation (Segmentacja scen)

**Problem**: Nie rozróżniamy typów scen.

**Rozwiązanie**: Klasyfikuj scenę i użyj odpowiedniego pipeline:

```python
class SceneClassifier:
    SCENES = {
        'static': {'interval': 10, 'llm': 'moondream'},
        'low_activity': {'interval': 5, 'llm': 'moondream'},
        'high_activity': {'interval': 2, 'llm': 'llava:7b'},
        'emergency': {'interval': 0.5, 'llm': 'llava:13b'},
    }
    
    def classify(self, frame_analysis):
        motion = frame_analysis.get('motion_percent', 0)
        person_count = len(frame_analysis.get('detections', []))
        
        if motion > 30 or person_count > 2:
            return 'high_activity'
        elif motion > 5 or person_count > 0:
            return 'low_activity'
        else:
            return 'static'
    
    def get_config(self, scene_type):
        return self.SCENES.get(scene_type, self.SCENES['static'])
```

---

### 8. 🔊 Streaming LLM Response

**Problem**: Czekamy na pełną odpowiedź LLM.

**Rozwiązanie**: Stream tokens i mów/wyświetlaj na bieżąco:

```python
class StreamingNarrator:
    async def narrate_streaming(self, frame_path):
        prompt = self._build_prompt(frame_path)
        
        buffer = ""
        async for token in self.llm.stream(prompt, image=frame_path):
            buffer += token
            
            # Speak complete sentences
            if '.' in buffer or '!' in buffer:
                sentence, buffer = buffer.rsplit('.', 1)
                await self.tts.speak_async(sentence + '.')
```

---

## Implementacja Priorytetowa

### Faza 1 (Quick Wins) - 1-2 dni
1. ✅ Zmiana modelu na llava:7b
2. [ ] Keyframe extraction
3. [ ] Smart compression (crop to detection)

### Faza 2 (Medium Impact) - 3-5 dni
4. [ ] Hierarchical processing
5. [ ] Response caching
6. [ ] Scene classification

### Faza 3 (Advanced) - 1-2 tygodnie
7. [ ] Batch processing
8. [ ] Async pipeline
9. [ ] Streaming LLM response

---

## Benchmark Targets

| Optymalizacja | Obecny czas | Target | Poprawa |
|---------------|-------------|--------|---------|
| Keyframes | 2-4s/frame | 2-4s/keyframe | 50% mniej LLM calls |
| Hierarchical | 2-4s always | 300ms-2s | Adaptacyjny |
| Batch (3 frames) | 6-12s | 3-4s | 60% szybciej |
| Caching | 2-4s repeated | 0ms cached | 90%+ dla static |
| **Combined** | **2-4s** | **0.5-2s avg** | **~3x faster** |

---

## Quick Start - Włączenie optymalizacji

```bash
# Użyj llava:7b (domyślnie teraz)
sq live narrator --url "rtsp://camera/stream" --mode track --focus person --tts

# Z adaptive intervals
sq live narrator --url "rtsp://camera/stream" --mode track --focus person --tts --adaptive

# Fast mode (moondream + aggressive caching)
sq live narrator --url "rtsp://camera/stream" --mode track --focus person --tts --fast

# High accuracy (llava:13b)
sq live narrator --url "rtsp://camera/stream" --mode track --focus person --tts --model llava:13b
```
