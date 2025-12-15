#!/bin/bash
# =============================================================================
# LLM Models ISO Builder
# Creates a separate ISO with compressed LLM models for offline use
#
# This ISO is meant to be used alongside the main Live ISO:
# 1. Boot from main ISO
# 2. Mount models ISO
# 3. Copy/link models to appropriate locations
#
# Models are compressed with zstd for smaller size
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_DIR="${CACHE_DIR:-$SCRIPT_DIR/cache}"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/output}"
MODELS_ISO_NAME="${MODELS_ISO_NAME:-llm-models.iso}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}✓${NC} $*"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $*"; }
log_error() { echo -e "${RED}✗${NC} $*"; }

echo "=========================================="
echo "LLM Models ISO Builder"
echo "=========================================="
echo "Output: $OUTPUT_DIR/$MODELS_ISO_NAME"
echo ""

# Create directories
mkdir -p "$CACHE_DIR/models" "$CACHE_DIR/tmp" "$OUTPUT_DIR"

# Temp directory for ISO content
WORK_DIR=$(mktemp -d -p "$CACHE_DIR/tmp" models-iso-XXXXXX)
MODELS_ROOT="$WORK_DIR/models"
mkdir -p "$MODELS_ROOT"

cleanup() {
    [ -d "$WORK_DIR" ] && rm -rf "$WORK_DIR"
}
trap cleanup EXIT

# =============================================================================
# Download Models
# =============================================================================

echo "[1/4] Preparing models..."

# Ollama models directory
OLLAMA_MODELS="$MODELS_ROOT/ollama"
mkdir -p "$OLLAMA_MODELS"

# GGUF models directory  
GGUF_MODELS="$MODELS_ROOT/gguf"
mkdir -p "$GGUF_MODELS"

# Check for existing Ollama models
OLLAMA_HOME="${OLLAMA_HOME:-$HOME/.ollama}"
if [ -d "$OLLAMA_HOME/models" ]; then
    log_info "Found Ollama models in $OLLAMA_HOME/models"
    
    # List available models
    echo "  Available Ollama models:"
    find "$OLLAMA_HOME/models" -name "*.bin" -o -name "*.gguf" 2>/dev/null | while read f; do
        size=$(du -h "$f" | cut -f1)
        echo "    - $(basename $f) ($size)"
    done
    
    # Copy models
    log_info "Copying Ollama models..."
    cp -r "$OLLAMA_HOME/models"/* "$OLLAMA_MODELS/" 2>/dev/null || true
else
    log_warn "No Ollama models found in $OLLAMA_HOME"
    log_info "To add Ollama models, run: ollama pull llama3.2:3b"
fi

# Check for GGUF models in project
ENV_DIR="$(dirname "$SCRIPT_DIR")"
if [ -d "$ENV_DIR/llama-cpp-rocm/models" ]; then
    log_info "Found GGUF models in llama-cpp-rocm/models"
    cp -r "$ENV_DIR/llama-cpp-rocm/models"/* "$GGUF_MODELS/" 2>/dev/null || true
fi

# Download popular GGUF models if none exist
if [ -z "$(ls -A $GGUF_MODELS 2>/dev/null)" ]; then
    log_info "Downloading recommended GGUF models..."
    
    # Small, fast model for testing
    GGUF_URL="https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    GGUF_NAME="tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    
    if [ ! -f "$CACHE_DIR/models/$GGUF_NAME" ]; then
        log_info "Downloading $GGUF_NAME (~700MB)..."
        curl -L "$GGUF_URL" -o "$CACHE_DIR/models/$GGUF_NAME" --progress-bar || {
            log_warn "Failed to download model, continuing without it"
        }
    fi
    
    if [ -f "$CACHE_DIR/models/$GGUF_NAME" ]; then
        cp "$CACHE_DIR/models/$GGUF_NAME" "$GGUF_MODELS/"
    fi
fi

echo ""

# =============================================================================
# Compress Models
# =============================================================================

echo "[2/4] Compressing models..."

# Check for compression tools
if command -v zstd &> /dev/null; then
    COMPRESS_CMD="zstd"
    COMPRESS_EXT=".zst"
    log_info "Using zstd compression (best ratio)"
elif command -v xz &> /dev/null; then
    COMPRESS_CMD="xz"
    COMPRESS_EXT=".xz"
    log_info "Using xz compression"
elif command -v gzip &> /dev/null; then
    COMPRESS_CMD="gzip"
    COMPRESS_EXT=".gz"
    log_info "Using gzip compression"
else
    COMPRESS_CMD=""
    log_warn "No compression tool found, models will be uncompressed"
fi

# Compress large files
COMPRESSED_DIR="$MODELS_ROOT/compressed"
mkdir -p "$COMPRESSED_DIR"

if [ -n "$COMPRESS_CMD" ]; then
    find "$MODELS_ROOT" -type f \( -name "*.gguf" -o -name "*.bin" -o -name "*.safetensors" \) -size +100M | while read model; do
        name=$(basename "$model")
        log_info "Compressing $name..."
        
        case $COMPRESS_CMD in
            zstd)
                zstd -T0 -19 "$model" -o "$COMPRESSED_DIR/${name}${COMPRESS_EXT}" 2>/dev/null
                ;;
            xz)
                xz -9 -c "$model" > "$COMPRESSED_DIR/${name}${COMPRESS_EXT}"
                ;;
            gzip)
                gzip -9 -c "$model" > "$COMPRESSED_DIR/${name}${COMPRESS_EXT}"
                ;;
        esac
        
        # Remove original if compression succeeded
        if [ -f "$COMPRESSED_DIR/${name}${COMPRESS_EXT}" ]; then
            rm "$model"
            orig_size=$(du -h "$model" 2>/dev/null | cut -f1 || echo "?")
            comp_size=$(du -h "$COMPRESSED_DIR/${name}${COMPRESS_EXT}" | cut -f1)
            log_success "  $name: compressed to $comp_size"
        fi
    done
fi

echo ""

# =============================================================================
# Create README and Scripts
# =============================================================================

echo "[3/4] Creating documentation..."

cat > "$MODELS_ROOT/README.md" << 'EOF'
# LLM Models ISO

This ISO contains pre-downloaded LLM models for offline use.

## Contents

- `ollama/` - Ollama model files
- `gguf/` - GGUF format models for llama.cpp
- `compressed/` - Compressed models (decompress before use)

## Usage

### Mount this ISO
```bash
sudo mkdir -p /mnt/models
sudo mount /dev/sr1 /mnt/models  # or wherever the ISO is
```

### For Ollama
```bash
# Copy to Ollama models directory
cp -r /mnt/models/ollama/* ~/.ollama/models/

# Or create symlink
ln -s /mnt/models/ollama ~/.ollama/models
```

### For llama.cpp
```bash
# Decompress if needed
cd /mnt/models/compressed
zstd -d *.zst  # or xz -d *.xz or gunzip *.gz

# Use with llama.cpp
./llama-server -m /mnt/models/gguf/model.gguf
```

## Decompression

If models are compressed:
```bash
# zstd (recommended)
zstd -d model.gguf.zst

# xz
xz -d model.gguf.xz

# gzip
gunzip model.gguf.gz
```
EOF

# Create install script
cat > "$MODELS_ROOT/install-models.sh" << 'INSTALL'
#!/bin/bash
# Install models from this ISO to the system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OLLAMA_HOME="${OLLAMA_HOME:-$HOME/.ollama}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-/opt/llm-station/llama-cpp-rocm}"

echo "Installing LLM models..."

# Decompress if needed
if [ -d "$SCRIPT_DIR/compressed" ]; then
    echo "Decompressing models..."
    cd "$SCRIPT_DIR/compressed"
    
    for f in *.zst; do
        [ -f "$f" ] && zstd -d "$f" 2>/dev/null && rm "$f"
    done
    for f in *.xz; do
        [ -f "$f" ] && xz -d "$f" 2>/dev/null
    done
    for f in *.gz; do
        [ -f "$f" ] && gunzip "$f" 2>/dev/null
    done
    
    # Move decompressed to gguf
    mv *.gguf ../gguf/ 2>/dev/null || true
    mv *.bin ../ollama/ 2>/dev/null || true
    cd -
fi

# Install Ollama models
if [ -d "$SCRIPT_DIR/ollama" ] && [ "$(ls -A $SCRIPT_DIR/ollama)" ]; then
    echo "Installing Ollama models to $OLLAMA_HOME/models..."
    mkdir -p "$OLLAMA_HOME/models"
    cp -r "$SCRIPT_DIR/ollama"/* "$OLLAMA_HOME/models/"
    echo "✓ Ollama models installed"
fi

# Install GGUF models
if [ -d "$SCRIPT_DIR/gguf" ] && [ "$(ls -A $SCRIPT_DIR/gguf)" ]; then
    echo "Installing GGUF models to $LLAMA_CPP_DIR/models..."
    mkdir -p "$LLAMA_CPP_DIR/models"
    cp -r "$SCRIPT_DIR/gguf"/* "$LLAMA_CPP_DIR/models/"
    echo "✓ GGUF models installed"
fi

echo ""
echo "Installation complete!"
echo "Models are ready to use."
INSTALL

chmod +x "$MODELS_ROOT/install-models.sh"

echo ""

# =============================================================================
# Create ISO
# =============================================================================

echo "[4/4] Creating ISO..."

# Calculate size
TOTAL_SIZE=$(du -sh "$MODELS_ROOT" | cut -f1)
log_info "Total models size: $TOTAL_SIZE"

ISO_OUTPUT="$OUTPUT_DIR/$MODELS_ISO_NAME"

if command -v xorriso &> /dev/null; then
    xorriso -as mkisofs \
        -o "$ISO_OUTPUT" \
        -iso-level 3 \
        -R -J -joliet-long \
        -V "LLM_MODELS" \
        "$MODELS_ROOT"
elif command -v genisoimage &> /dev/null; then
    genisoimage \
        -o "$ISO_OUTPUT" \
        -R -J -joliet-long \
        -V "LLM_MODELS" \
        "$MODELS_ROOT"
else
    log_error "No ISO creation tool found (install xorriso)"
    exit 1
fi

# Generate checksums
cd "$OUTPUT_DIR"
sha256sum "$MODELS_ISO_NAME" > "${MODELS_ISO_NAME}.sha256"

ISO_SIZE=$(du -h "$ISO_OUTPUT" | cut -f1)

echo ""
echo "=========================================="
echo "Models ISO creation complete!"
echo "=========================================="
echo ""
echo "Output: $ISO_OUTPUT"
echo "Size: $ISO_SIZE"
echo ""
echo "Contents:"
ls -lh "$MODELS_ROOT"/*/ 2>/dev/null | head -20
echo ""
echo "Usage:"
echo "  1. Boot from main LLM Station ISO"
echo "  2. Mount models ISO: sudo mount /dev/sr1 /mnt/models"
echo "  3. Install: /mnt/models/install-models.sh"
echo "=========================================="
