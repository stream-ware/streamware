#!/bin/bash
# =============================================================================
# Install fast models for Streamware Live Narrator
# =============================================================================
# This script installs:
# - moondream: Fast vision model (~1.5s response time)
# - gemma:2b: Fast guarder model (~0.25s response time)
# - ultralytics (YOLO): Fast object detection (~10ms)
#
# Usage:
#   ./install_fast_model.sh        # Install all (recommended)
#   ./install_fast_model.sh --llm  # LLM models only (no YOLO)
#   ./install_fast_model.sh --yolo # YOLO only
# =============================================================================

set -e

INSTALL_LLM=true
INSTALL_YOLO=true

# Parse arguments
for arg in "$@"; do
    case $arg in
        --llm)
            INSTALL_YOLO=false
            ;;
        --yolo)
            INSTALL_LLM=false
            ;;
        --help|-h)
            echo "Usage: $0 [--llm] [--yolo]"
            echo "  --llm   Install only LLM models (moondream, gemma:2b)"
            echo "  --yolo  Install only YOLO (ultralytics)"
            echo "  (default: install all)"
            exit 0
            ;;
    esac
done

echo "🚀 Installing fast models for Streamware..."
echo ""

# Install LLM models
if [ "$INSTALL_LLM" = true ]; then
    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "❌ Ollama is not running. Please start it first:"
        echo "   ollama serve"
        exit 1
    fi

    echo "✅ Ollama is running"

    # Pull moondream model (fast vision model, ~1.8B params)
    echo ""
    echo "📦 Pulling moondream model (~1.7GB)..."
    echo "   This is a fast vision model optimized for real-time analysis"
    ollama pull moondream

    # Also ensure we have a fast guarder model (gemma:2b is faster than gemma2:2b)
    echo ""
    echo "📦 Pulling gemma:2b (fast guarder model)..."
    ollama pull gemma:2b
fi

# Install YOLO
if [ "$INSTALL_YOLO" = true ]; then
    echo ""
    echo "📦 Installing YOLO (ultralytics)..."
    pip install ultralytics -q
    echo "✅ YOLO installed"
fi

# Verify installation
echo ""
echo "✅ Models installed successfully!"
echo ""
echo "📊 Installed models for fast processing:"
ollama list | grep -E "moondream|gemma:2b" || true

# Update .env if it exists
ENV_FILE="${HOME}/github/stream-ware/streamware/.env"
if [ -f "$ENV_FILE" ]; then
    echo ""
    echo "📝 Updating .env with fast model settings..."
    
    # Backup
    cp "$ENV_FILE" "${ENV_FILE}.bak"
    
    # Update or add SQ_MODEL
    if grep -q "^SQ_MODEL=" "$ENV_FILE"; then
        sed -i 's/^SQ_MODEL=.*/SQ_MODEL=moondream/' "$ENV_FILE"
    else
        echo "SQ_MODEL=moondream" >> "$ENV_FILE"
    fi
    
    # Update or add SQ_GUARDER_MODEL  
    if grep -q "^SQ_GUARDER_MODEL=" "$ENV_FILE"; then
        sed -i 's/^SQ_GUARDER_MODEL=.*/SQ_GUARDER_MODEL=gemma:2b/' "$ENV_FILE"
    else
        echo "SQ_GUARDER_MODEL=gemma:2b" >> "$ENV_FILE"
    fi
    
    # Enable fast capture
    if grep -q "^SQ_FAST_CAPTURE=" "$ENV_FILE"; then
        sed -i 's/^SQ_FAST_CAPTURE=.*/SQ_FAST_CAPTURE=true/' "$ENV_FILE"
    else
        echo "SQ_FAST_CAPTURE=true" >> "$ENV_FILE"
    fi
    
    # Enable YOLO
    if grep -q "^SQ_USE_YOLO=" "$ENV_FILE"; then
        sed -i 's/^SQ_USE_YOLO=.*/SQ_USE_YOLO=true/' "$ENV_FILE"
    else
        echo "SQ_USE_YOLO=true" >> "$ENV_FILE"
    fi
    
    # Set track mode as default
    if grep -q "^SQ_STREAM_MODE=" "$ENV_FILE"; then
        sed -i 's/^SQ_STREAM_MODE=.*/SQ_STREAM_MODE=track/' "$ENV_FILE"
    else
        echo "SQ_STREAM_MODE=track" >> "$ENV_FILE"
    fi
    
    # Set person as default focus
    if grep -q "^SQ_STREAM_FOCUS=" "$ENV_FILE"; then
        sed -i 's/^SQ_STREAM_FOCUS=.*/SQ_STREAM_FOCUS=person/' "$ENV_FILE"
    else
        echo "SQ_STREAM_FOCUS=person" >> "$ENV_FILE"
    fi
    
    echo "✅ .env updated with fast settings"
fi

echo ""
echo "🎉 Fast model setup complete!"
echo ""
echo "Expected performance improvements:"
echo "  ┌────────────────┬────────────┬────────────┬──────────────┐"
echo "  │ Component      │ Before     │ After      │ Improvement  │"
echo "  ├────────────────┼────────────┼────────────┼──────────────┤"
echo "  │ YOLO detection │ N/A (HOG)  │ ~10ms      │ 10x faster   │"
echo "  │ Frame capture  │ ~4000ms    │ ~0ms       │ FastCapture  │"
echo "  │ Vision LLM     │ ~4000ms    │ ~1500ms    │ moondream    │"
echo "  │ Guarder LLM    │ ~2700ms    │ ~250ms     │ gemma:2b     │"
echo "  ├────────────────┼────────────┼────────────┼──────────────┤"
echo "  │ Total cycle    │ ~10s       │ ~2s        │ 80% faster   │"
echo "  └────────────────┴────────────┴────────────┴──────────────┘"
echo ""
echo "Usage examples:"
echo ""
echo "  # Person tracking with voice:"
echo "  sq live narrator --url 'rtsp://camera/stream' --mode track --focus person --tts"
echo ""
echo "  # Bird feeder monitoring:"
echo "  sq live narrator --url 'rtsp://birdcam/stream' --mode track --focus bird --tts"
echo ""
echo "  # Pet camera:"
echo "  sq live narrator --url 'rtsp://petcam/stream' --mode track --focus pet --tts"
echo ""
echo "  # With verbose timing:"
echo "  sq live narrator --url 'rtsp://camera/stream' --mode track --focus person --tts --verbose"
