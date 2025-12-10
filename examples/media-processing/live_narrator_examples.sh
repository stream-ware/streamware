#!/bin/bash
# =============================================================================
# Live Narrator Examples - Real-time Video Analysis with AI
# =============================================================================
# 
# Live Narrator uses YOLO + Vision LLM for fast, accurate detection.
# Features: FastCapture, Object Tracking, Animal Detection, TTS
#
# Requirements:
#   - Ollama with moondream model
#   - YOLO (auto-installed on first use)
#   - Optional: pyttsx3 for TTS
#
# Install fast models:
#   ./install_fast_model.sh
#   # or manually:
#   ollama pull moondream
#   ollama pull gemma:2b
# =============================================================================

set -e

# -----------------------------------------------------------------------------
# BASIC USAGE
# -----------------------------------------------------------------------------

# Basic person tracking with TTS
echo "🎯 Basic person tracking..."
sq live narrator \
    --url "rtsp://admin:password@192.168.1.100:554/stream" \
    --mode track \
    --focus person \
    --tts \
    --duration 60

# Verbose mode (see all processing steps)
echo "📊 Verbose mode with timing..."
sq live narrator \
    --url "rtsp://admin:password@192.168.1.100:554/stream" \
    --mode track \
    --focus person \
    --tts \
    --verbose \
    --duration 60

# -----------------------------------------------------------------------------
# ANIMAL DETECTION (NEW!)
# -----------------------------------------------------------------------------

# Bird feeder monitoring
echo "🐦 Bird feeder monitoring..."
sq live narrator \
    --url "rtsp://192.168.1.101:554/birdcam" \
    --mode track \
    --focus bird \
    --tts \
    --verbose \
    --duration 300  # 5 minutes

# Cat/Dog detection (pet cam)
echo "🐱 Pet monitoring..."
sq live narrator \
    --url "rtsp://192.168.1.102:554/petcam" \
    --mode track \
    --focus pet \
    --tts \
    --duration 120

# All animals
echo "🦁 Wildlife camera..."
sq live narrator \
    --url "rtsp://192.168.1.103:554/wildlife" \
    --mode track \
    --focus animal \
    --tts \
    --duration 600  # 10 minutes

# -----------------------------------------------------------------------------
# DIFFERENT MODES
# -----------------------------------------------------------------------------

# Track mode - follow specific objects
sq live narrator \
    --url "rtsp://camera/stream" \
    --mode track \
    --focus person \
    --tts

# Diff mode - report only changes
sq live narrator \
    --url "rtsp://camera/stream" \
    --mode diff \
    --tts

# Full mode - complete scene descriptions
sq live narrator \
    --url "rtsp://camera/stream" \
    --mode full \
    --tts

# -----------------------------------------------------------------------------
# PERFORMANCE OPTIONS
# -----------------------------------------------------------------------------

# Fast mode with moondream (recommended)
sq live narrator \
    --url "rtsp://camera/stream" \
    --mode track \
    --focus person \
    --model moondream \
    --tts

# High quality with llava:13b (slower but more accurate)
sq live narrator \
    --url "rtsp://camera/stream" \
    --mode track \
    --focus person \
    --model llava:13b \
    --tts

# Adjust interval (seconds between analyses)
sq live narrator \
    --url "rtsp://camera/stream" \
    --mode track \
    --focus person \
    --interval 2 \
    --tts

# -----------------------------------------------------------------------------
# OUTPUT OPTIONS
# -----------------------------------------------------------------------------

# Save to HTML report
sq live narrator \
    --url "rtsp://camera/stream" \
    --mode track \
    --focus person \
    --file report.html \
    --frames-dir ./frames \
    --duration 120

# Save frames with annotations
sq live narrator \
    --url "rtsp://camera/stream" \
    --mode track \
    --focus person \
    --frames-dir ./captured_frames \
    --tts

# Quiet mode (no terminal output, only TTS)
sq live narrator \
    --url "rtsp://camera/stream" \
    --mode track \
    --focus person \
    --tts \
    --quiet

# Lite mode (less RAM usage)
sq live narrator \
    --url "rtsp://camera/stream" \
    --mode track \
    --focus person \
    --lite \
    --tts

# -----------------------------------------------------------------------------
# TRIGGERS (Alerts)
# -----------------------------------------------------------------------------

# Alert when specific words detected
sq live narrator \
    --url "rtsp://camera/stream" \
    --mode track \
    --focus person \
    --trigger "running,falling,fighting" \
    --tts

# Webhook notification on trigger
sq live narrator \
    --url "rtsp://camera/stream" \
    --mode track \
    --focus person \
    --trigger "intruder,unknown person" \
    --webhook "https://hooks.slack.com/..." \
    --tts

# -----------------------------------------------------------------------------
# VEHICLE TRACKING
# -----------------------------------------------------------------------------

# Track vehicles
sq live narrator \
    --url "rtsp://parking-cam/stream" \
    --mode track \
    --focus vehicle \
    --tts

# -----------------------------------------------------------------------------
# YOUTUBE/TWITCH STREAMS
# -----------------------------------------------------------------------------

# Analyze YouTube live stream
sq live narrator \
    --url "https://www.youtube.com/watch?v=LIVE_ID" \
    --mode track \
    --focus person \
    --duration 60

# -----------------------------------------------------------------------------
# WEBCAM
# -----------------------------------------------------------------------------

# Local webcam
sq live narrator \
    --url "webcam://0" \
    --mode track \
    --focus person \
    --tts

# -----------------------------------------------------------------------------
# ENVIRONMENT VARIABLES
# -----------------------------------------------------------------------------

# Set default model and options in .env:
# SQ_MODEL=moondream
# SQ_GUARDER_MODEL=gemma:2b
# SQ_STREAM_MODE=track
# SQ_STREAM_FOCUS=person
# SQ_FAST_CAPTURE=true
# SQ_USE_YOLO=true

# Then just run:
sq live narrator --url "rtsp://camera/stream" --tts

echo "✅ Examples complete!"
