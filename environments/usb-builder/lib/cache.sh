#!/bin/bash
# =============================================================================
# Cache Management Library
# Source this file: source "$(dirname "$0")/lib/cache.sh"
# =============================================================================

# Requires common.sh to be sourced first
[ -z "$RED" ] && source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# =============================================================================
# Cache Configuration
# =============================================================================

# Default cache directory (can be overridden)
CACHE_DIR="${CACHE_DIR:-$(dirname "${BASH_SOURCE[0]}")/../cache}"

# Cache subdirectories
CACHE_ISO_DIR="$CACHE_DIR/iso"
CACHE_IMAGES_DIR="$CACHE_DIR/images"
CACHE_MODELS_DIR="$CACHE_DIR/models"

# =============================================================================
# Cache Initialization
# =============================================================================

# Initialize cache directories
cache_init() {
    ensure_dir "$CACHE_ISO_DIR"
    ensure_dir "$CACHE_IMAGES_DIR"
    ensure_dir "$CACHE_MODELS_DIR"
}

# =============================================================================
# ISO Cache
# =============================================================================

# Check if ISO is cached and valid
cache_has_iso() {
    local iso_name="$1"
    local min_size="${2:-500000000}"  # 500MB minimum
    local cached="$CACHE_ISO_DIR/$iso_name"
    
    is_valid_iso "$cached" "$min_size"
}

# Get cached ISO path
cache_get_iso() {
    local iso_name="$1"
    echo "$CACHE_ISO_DIR/$iso_name"
}

# Download and cache ISO
cache_download_iso() {
    local url="$1"
    local iso_name="$2"
    local cached="$CACHE_ISO_DIR/$iso_name"
    
    cache_init
    
    if cache_has_iso "$iso_name"; then
        local size=$(file_size_human "$cached")
        log_success "Using cached ISO: $cached ($size)"
        echo "$cached"
        return 0
    fi
    
    # Remove corrupted file if exists
    if [ -f "$cached" ]; then
        log_warn "Removing corrupted cached ISO..."
        rm -f "$cached"
    fi
    
    log_info "Downloading ISO (will be cached)..."
    curl -L "$url" -o "$cached" --progress-bar -C -
    
    if cache_has_iso "$iso_name"; then
        log_success "ISO cached successfully"
        echo "$cached"
        return 0
    else
        log_error "Downloaded ISO appears corrupted"
        rm -f "$cached"
        return 1
    fi
}

# =============================================================================
# Container Image Cache
# =============================================================================

# Check if container image is cached
cache_has_image() {
    local image_name="$1"
    local tar_name=$(echo "$image_name" | tr '/:' '-').tar
    local cached="$CACHE_IMAGES_DIR/$tar_name"
    
    [ -f "$cached" ] && [ -s "$cached" ]
}

# Get cached image path
cache_get_image() {
    local image_name="$1"
    local tar_name=$(echo "$image_name" | tr '/:' '-').tar
    echo "$CACHE_IMAGES_DIR/$tar_name"
}

# List cached images
cache_list_images() {
    if [ -d "$CACHE_IMAGES_DIR" ]; then
        ls -1 "$CACHE_IMAGES_DIR"/*.tar 2>/dev/null
    fi
}

# Get cache size
cache_size() {
    local dir="${1:-$CACHE_DIR}"
    du -sh "$dir" 2>/dev/null | cut -f1
}

# =============================================================================
# Cache Cleanup
# =============================================================================

# Clean ISO cache
cache_clean_iso() {
    log_info "Cleaning ISO cache..."
    rm -rf "$CACHE_ISO_DIR"/*
    log_success "ISO cache cleaned"
}

# Clean images cache
cache_clean_images() {
    log_info "Cleaning container images cache..."
    rm -rf "$CACHE_IMAGES_DIR"/*
    log_success "Images cache cleaned"
}

# Clean all cache
cache_clean_all() {
    log_info "Cleaning all cache..."
    rm -rf "$CACHE_DIR"/*
    cache_init
    log_success "All cache cleaned"
}

# =============================================================================
# Cache Status
# =============================================================================

# Print cache status
cache_status() {
    echo "=== Cache Status ==="
    echo "Location: $CACHE_DIR"
    echo ""
    
    echo "ISO cache:"
    if [ -d "$CACHE_ISO_DIR" ]; then
        local iso_count=$(ls "$CACHE_ISO_DIR"/*.iso 2>/dev/null | wc -l)
        if [ "$iso_count" -gt 0 ]; then
            local iso_size=$(cache_size "$CACHE_ISO_DIR")
            echo "  $iso_count file(s), $iso_size"
            ls -1h "$CACHE_ISO_DIR"/*.iso 2>/dev/null | sed 's/^/    /'
        else
            echo "  (empty)"
        fi
    else
        echo "  (not initialized)"
    fi
    echo ""
    
    echo "Container images:"
    if [ -d "$CACHE_IMAGES_DIR" ]; then
        local img_count=$(ls "$CACHE_IMAGES_DIR"/*.tar 2>/dev/null | wc -l)
        if [ "$img_count" -gt 0 ]; then
            local img_size=$(cache_size "$CACHE_IMAGES_DIR")
            echo "  $img_count file(s), $img_size"
            ls -1h "$CACHE_IMAGES_DIR"/*.tar 2>/dev/null | sed 's/^/    /'
        else
            echo "  (empty)"
        fi
    else
        echo "  (not initialized)"
    fi
    echo ""
    
    echo "Total cache size: $(cache_size)"
}
