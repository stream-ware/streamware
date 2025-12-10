# Streamware Architecture

## 📊 Current State Analysis

### Identified Duplications

| Location | Issue | Solution |
|----------|-------|----------|
| `api/generate` calls | 12+ places calling Ollama directly | Use `llm_client.py` everywhere |
| `_call_vision_model` | Duplicated in motion_diff.py, tracking.py | Extract to llm_client |
| TTS code | Was in live_narrator.py + voice.py | ✅ Fixed → `tts.py` |
| env file updates | Was in cli.py + setup.py | ✅ Fixed → `setup_utils.py` |
| "No significant" filtering | In 5+ components | Centralize in response validator |

### Module Dependencies (Current)

```
┌──────────────────────────────────────────────────────────────┐
│                        quick_cli.py                          │
│                       (121KB - main CLI)                     │
└──────────────────────┬───────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌───────────┐  ┌───────────────┐  ┌────────────┐
│  core.py  │  │ components/*  │  │  config.py │
│  (flow)   │  │ (12 modules)  │  │            │
└───────────┘  └───────┬───────┘  └────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌───────────────┐ ┌────────────┐ ┌─────────────────┐
│ llm_client.py │ │   tts.py   │ │ image_optimize.py│
│ (centralized) │ │ (unified)  │ │                 │
└───────────────┘ └────────────┘ └─────────────────┘
```

---

## 🎯 Refactoring Plan

### Phase 1: Consolidate LLM Calls ✅ (Partial)

**Status:** llm_client.py created, needs adoption

**Tasks:**
1. Update `motion_diff.py` → use `llm_client.vision_query()`
2. Update `tracking.py` → use `llm_client.vision_query()`
3. Update `stream.py` → use `llm_client.vision_query()`
4. Update `smart_monitor.py` → use `llm_client.vision_query()`
5. Update `live_narrator.py` → ✅ Done for `_describe_frame_advanced`
6. Update `media.py` → use `llm_client.vision_query()`

### Phase 2: Response Validation / Filtering

**Goal:** Don't log "nothing happened" responses

**Create `response_filter.py`:**
```python
def is_significant_response(response: str, mode: str = "general") -> bool:
    """Check if LLM response contains meaningful information."""
    noise_patterns = [
        "no significant changes",
        "no movement detected", 
        "no person visible",
        "nothing to report",
        "VISIBLE: NO",
        "PRESENT: NO",
        "CHANGED: NO",
    ]
    response_lower = response.lower()
    return not any(p in response_lower for p in noise_patterns)

def filter_for_logging(response: str) -> Optional[str]:
    """Return response only if significant, else None."""
    if is_significant_response(response):
        return response
    return None
```

### Phase 3: REST API Server

**Create `api_server.py`:**
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Streamware API")

class AnalyzeRequest(BaseModel):
    image_url: str
    prompt: str
    model: str = "llava:7b"

@app.post("/api/v1/analyze")
async def analyze_image(req: AnalyzeRequest):
    from .llm_client import vision_query
    result = vision_query(req.image_url, req.prompt)
    return {"result": result}

@app.post("/api/v1/live/start")
async def start_live(source: str, mode: str = "track", focus: str = "person"):
    """Start live narrator session"""
    ...

@app.get("/api/v1/live/{session_id}/status")
async def get_live_status(session_id: str):
    ...

@app.post("/api/v1/speak")
async def speak(text: str, engine: str = "auto"):
    from .tts import speak
    success = speak(text)
    return {"success": success}
```

### Phase 4: LLM-Driven Client

**Create `llm_agent.py`:**
```python
class StreamwareAgent:
    """Agent that can be controlled by LLM."""
    
    SYSTEM_PROMPT = '''You are a Streamware automation agent.
    Available commands:
    - analyze_image(path, prompt) - Analyze image with vision LLM
    - start_watch(url, focus) - Start watching camera
    - speak(text) - Speak via TTS
    - query_network() - Scan network for devices
    
    Respond with JSON: {"action": "...", "params": {...}}
    '''
    
    def execute(self, llm_response: dict):
        action = llm_response.get("action")
        params = llm_response.get("params", {})
        
        if action == "analyze_image":
            return vision_query(**params)
        elif action == "start_watch":
            return self._start_watch(**params)
        elif action == "speak":
            return speak(**params)
```

---

## 📐 Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ REST API    │  │ CLI (sq)    │  │ Python DSL (Pipeline)  │ │
│  │ (FastAPI)   │  │ (quick_cli) │  │ (dsl.py)               │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
└─────────┼────────────────┼─────────────────────┼───────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Service Layer                          │
│  ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │ llm_client.py │  │ response_      │  │ session_manager  │   │
│  │ (all LLM)     │  │ filter.py      │  │ (live sessions)  │   │
│  └───────────────┘  └────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Component Layer                             │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌─────────────────┐  │
│  │ stream   │ │ tracking   │ │ media    │ │ live_narrator   │  │
│  └──────────┘ └────────────┘ └──────────┘ └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Infrastructure Layer                         │
│  ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │ tts.py        │  │ setup_utils.py │  │ image_optimize   │   │
│  │ (voice)       │  │ (install)      │  │ (preprocessing)  │   │
│  └───────────────┘  └────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Communication Flow

### Current Flow (sq live --tts)
```
User → quick_cli.py → LiveNarratorComponent
                              │
                              ├─→ ffmpeg (capture)
                              ├─→ FrameAnalyzer (motion)
                              ├─→ requests.post(ollama) ← DUPLICATE
                              └─→ tts.speak()
```

### Target Flow
```
User → quick_cli.py → LiveNarratorComponent
                              │
                              ├─→ ffmpeg (capture)
                              ├─→ FrameAnalyzer (motion)
                              ├─→ llm_client.analyze_image()
                              │         │
                              │         └─→ response_filter.is_significant()
                              │                    │
                              │                    ├─→ True: log + tts
                              │                    └─→ False: skip
                              └─→ tts.speak() (only if significant)
```

---

## ✅ Completed

1. ✅ **`response_filter.py`** - filter noise from LLM responses
2. ✅ **Guarder model** - small LLM (qwen2.5:3b) validates responses before logging
3. ✅ **Significance check** in live_narrator - skip "no change" responses
4. ✅ **`--guarder` flag** - enable LLM validation via CLI
5. ✅ **`--lite` flag** - reduce memory usage

## 🔄 Next Steps

1. **Migrate all Ollama calls** to `llm_client.py` (partial)
2. **Create REST API** with FastAPI (optional)
3. **Create LLM Agent** for natural language control

---

## 🛡️ Guarder Model

Small LLM that validates vision model responses before logging:

```bash
# Enable via CLI
sq live narrator --url "rtsp://..." --guarder

# Or via .env
SQ_USE_GUARDER=true
SQ_GUARDER_MODEL=qwen2.5:3b
```

**Recommended models (3B, fast):**
| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| `qwen2.5:3b` | 2GB | Fast | Best |
| `phi3:mini` | 2.3GB | Fast | Good |
| `gemma2:2b` | 1.6GB | Fastest | OK |
| `llama3.2:3b` | 2GB | Fast | Good |

**Flow:**
```
Vision LLM (llava:7b) → Response → Guarder (qwen2.5:3b) → YES/NO → Log/Skip
```

**Auto-install at startup:**
```
sq live narrator --url "rtsp://..."

⚠️  Model qwen2.5:3b not found. Install with: ollama pull qwen2.5:3b

   Guarder model 'qwen2.5:3b' is needed for smart response filtering.
   Recommended models (small, fast):
   1. qwen2.5:3b  - Best quality (2GB)
   2. gemma2:2b   - Fastest (1.6GB)
   3. phi3:mini   - Good balance (2.3GB)
   4. Skip        - Use regex filtering only

   Install model? [1-4, default=1]: 1

   Pulling qwen2.5:3b... (this may take a few minutes)
   ✅ qwen2.5:3b installed successfully
```

---

## 📁 Module Structure

```
streamware/
├── cli.py              # Main CLI (streamware command)
├── quick_cli.py        # sq command (121KB)
├── core.py             # Flow engine
├── config.py           # Configuration management
├── dsl.py              # Python DSL (Pipeline)
│
├── llm_client.py       # Centralized LLM client ✅
├── tts.py              # Unified TTS module ✅
├── response_filter.py  # Smart response filtering ✅
├── image_optimize.py   # Image preprocessing
├── setup_utils.py      # Cross-platform setup ✅
│
├── prompts/            # External prompt templates
│   ├── __init__.py
│   ├── stream_diff.txt
│   ├── live_narrator_*.txt
│   └── ...
│
└── components/         # Core components
    ├── live_narrator.py
    ├── stream.py
    ├── tracking.py
    ├── motion_diff.py
    ├── smart_monitor.py
    └── ...
```
