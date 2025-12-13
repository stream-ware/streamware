#!/bin/bash
# =============================================================================
# Download GGUF models for llama.cpp
# Run this script BEFORE creating the USB to pre-download all models
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="$SCRIPT_DIR/models"

echo "=========================================="
echo "Downloading GGUF models for llama.cpp"
echo "Target: $MODELS_DIR"
echo "=========================================="

mkdir -p "$MODELS_DIR"

# Function to download from Hugging Face
download_model() {
    local repo=$1
    local file=$2
    local output=$3
    
    echo "Downloading: $output"
    curl -L "https://huggingface.co/$repo/resolve/main/$file" \
        -o "$MODELS_DIR/$output" \
        --progress-bar
}

# Recommended models for 16GB RAM with GGUF quantization
# Q4_K_M offers best balance of quality and speed

echo ""
echo "Select models to download:"
echo "  1) Llama 3.2 3B (Q4_K_M) - ~2GB - Fast, good quality"
echo "  2) Mistral 7B (Q4_K_M) - ~4GB - Balanced"
echo "  3) Phi-3 Mini (Q4_K_M) - ~2GB - Microsoft, fast"
echo "  4) CodeLlama 7B (Q4_K_M) - ~4GB - Code generation"
echo "  5) Qwen2.5 7B (Q4_K_M) - ~4GB - Multilingual"
echo "  6) DeepSeek Coder 6.7B (Q4_K_M) - ~4GB - Code"
echo "  A) All recommended (small + medium)"
echo ""
read -p "Enter choice (1-6, A, or comma-separated): " choice

download_llama32() {
    download_model "bartowski/Llama-3.2-3B-Instruct-GGUF" \
        "Llama-3.2-3B-Instruct-Q4_K_M.gguf" \
        "llama-3.2-3b-q4.gguf"
}

download_mistral() {
    download_model "TheBloke/Mistral-7B-Instruct-v0.2-GGUF" \
        "mistral-7b-instruct-v0.2.Q4_K_M.gguf" \
        "mistral-7b-q4.gguf"
}

download_phi3() {
    download_model "microsoft/Phi-3-mini-4k-instruct-gguf" \
        "Phi-3-mini-4k-instruct-q4.gguf" \
        "phi-3-mini-q4.gguf"
}

download_codellama() {
    download_model "TheBloke/CodeLlama-7B-Instruct-GGUF" \
        "codellama-7b-instruct.Q4_K_M.gguf" \
        "codellama-7b-q4.gguf"
}

download_qwen() {
    download_model "Qwen/Qwen2.5-7B-Instruct-GGUF" \
        "qwen2.5-7b-instruct-q4_k_m.gguf" \
        "qwen2.5-7b-q4.gguf"
}

download_deepseek() {
    download_model "TheBloke/deepseek-coder-6.7B-instruct-GGUF" \
        "deepseek-coder-6.7b-instruct.Q4_K_M.gguf" \
        "deepseek-coder-6.7b-q4.gguf"
}

case $choice in
    1) download_llama32 ;;
    2) download_mistral ;;
    3) download_phi3 ;;
    4) download_codellama ;;
    5) download_qwen ;;
    6) download_deepseek ;;
    [Aa])
        download_llama32
        download_phi3
        download_mistral
        download_codellama
        ;;
    *)
        IFS=',' read -ra CHOICES <<< "$choice"
        for c in "${CHOICES[@]}"; do
            case $c in
                1) download_llama32 ;;
                2) download_mistral ;;
                3) download_phi3 ;;
                4) download_codellama ;;
                5) download_qwen ;;
                6) download_deepseek ;;
            esac
        done
        ;;
esac

# Create default symlink
if [ -f "$MODELS_DIR/llama-3.2-3b-q4.gguf" ]; then
    ln -sf llama-3.2-3b-q4.gguf "$MODELS_DIR/model.gguf"
elif [ -f "$MODELS_DIR/phi-3-mini-q4.gguf" ]; then
    ln -sf phi-3-mini-q4.gguf "$MODELS_DIR/model.gguf"
else
    # Link first available model
    FIRST_MODEL=$(ls "$MODELS_DIR"/*.gguf 2>/dev/null | head -1)
    if [ -n "$FIRST_MODEL" ]; then
        ln -sf "$(basename $FIRST_MODEL)" "$MODELS_DIR/model.gguf"
    fi
fi

# Calculate size
TOTAL_SIZE=$(du -sh "$MODELS_DIR" | cut -f1)

echo ""
echo "=========================================="
echo "Download complete!"
echo "Models location: $MODELS_DIR"
echo "Total size: $TOTAL_SIZE"
echo ""
echo "Available models:"
ls -lh "$MODELS_DIR"/*.gguf 2>/dev/null || echo "No models found"
echo ""
echo "Default model: $(readlink -f $MODELS_DIR/model.gguf 2>/dev/null || echo 'none')"
echo "=========================================="
