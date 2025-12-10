# Streamware LLM Prompts

This directory contains all LLM prompts used by Streamware components.
**Prompts can be customized** by editing these files or via environment variables.

## 📁 Prompt Files

### Live Narrator (Track Mode)
| File | Description | Variables |
|------|-------------|-----------|
| `track_person.txt` | Person tracking prompt | `{context}`, `{movement_hint}`, `{motion_pct}` |
| `track_bird.txt` | Bird detection prompt | `{context}`, `{prev_info}` |
| `track_animal.txt` | Animal detection prompt | `{context}`, `{focus}` |

### Live Narrator (Other Modes)
| File | Description |
|------|-------------|
| `live_narrator_track.txt` | Generic track mode |
| `live_narrator_diff.txt` | Diff mode |
| `live_narrator_full.txt` | Full description mode |
| `live_narrator_advanced.txt` | Advanced analysis |

### Guarder (Response Filter)
| File | Description |
|------|-------------|
| `guarder_summarize.txt` | Summarize verbose responses |
| `guarder_compare.txt` | Compare states, detect NO_CHANGE |

### Media Processing
| File | Description |
|------|-------------|
| `media_frame_analyze.txt` | Single frame analysis |
| `media_frame_compare.txt` | Compare two frames |
| `media_video_summary.txt` | Video summary |

### Stream Analysis
| File | Description |
|------|-------------|
| `stream_diff.txt` | Stream diff mode |
| `stream_full.txt` | Stream full mode |
| `stream_focus.txt` | Focused stream analysis |

### Other
| File | Description |
|------|-------------|
| `motion_region.txt` | Motion region description |
| `tracking_detect.txt` | Object tracking |
| `trigger_check.txt` | Trigger condition check |
| `automation_task.txt` | Automation task parsing |
| `text2sq_system.txt` | Natural language to command |

## 🔧 Customization

### Option 1: Edit Files
Edit the `.txt` files directly. Changes take effect on next run.

### Option 2: Environment Variables
Override any prompt via `SQ_PROMPT_<NAME>`:

```bash
# Override track_person prompt
export SQ_PROMPT_TRACK_PERSON="Describe the person in the image briefly."

# Override guarder
export SQ_PROMPT_GUARDER_SUMMARIZE="Summarize in 5 words: {response}"
```

### Option 3: Python API
```python
from streamware.prompts import get_prompt, render_prompt, reload_prompts

# Get raw template
template = get_prompt("track_person")

# Render with variables
prompt = render_prompt("track_person", context="Motion detected", motion_pct="50")

# Reload after file changes
reload_prompts()
```

## 📝 Variables

Common variables used in prompts:

| Variable | Description | Example |
|----------|-------------|---------|
| `{context}` | Motion/analysis context | "Motion: 50% change" |
| `{focus}` | What to track | "person", "bird" |
| `{Focus}` | Capitalized focus | "Person", "Bird" |
| `{motion_pct}` | Motion percentage | "45" |
| `{prev_info}` | Previous description | "Person at desk" |
| `{prev_description}` | Full previous description | "..." |
| `{movement_hint}` | Movement analysis | "Person moving left" |
| `{activity_focus}` | Activity alert | "⚠️ SIGNIFICANT MOTION" |
| `{response}` | LLM response to filter | "..." |
| `{prev_summary}` | Previous summary | "Person: working" |

## 🎯 Best Practices

1. **Keep prompts short** - Small models work better with concise instructions
2. **Include examples** - Show expected output format
3. **Use clear format** - "Response format: ..." helps consistency
4. **Test changes** - Use `--verbose` to see prompt output
5. **Focus on activity** - For tracking, emphasize actions over static descriptions

## 📊 Testing Prompts

```bash
# Test with verbose mode to see prompts
sq live narrator --url "rtsp://camera/stream" --mode track --focus person --tts --verbose

# Look for:
# ⚪ [llm_prompt] sent: [moondream] ...
# ⚪ [llm_response] received: ...
```
