#!/bin/bash
# =============================================================================
# Container Operations Library
# Source this file: source "$(dirname "$0")/lib/container.sh"
# =============================================================================

# Requires common.sh and cache.sh to be sourced first
[ -z "$RED" ] && source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
[ -z "$CACHE_DIR" ] && source "$(dirname "${BASH_SOURCE[0]}")/cache.sh"

# =============================================================================
# Container Runtime Detection
# =============================================================================

# Detect container runtime (podman or docker)
detect_container_runtime() {
    if command_exists podman; then
        echo "podman"
    elif command_exists docker; then
        echo "docker"
    else
        echo ""
    fi
}

# Get container runtime command
CONTAINER_CMD=""
container_init() {
    CONTAINER_CMD=$(detect_container_runtime)
    if [ -z "$CONTAINER_CMD" ]; then
        log_warn "No container runtime found (podman/docker)"
        return 1
    fi
    return 0
}

# =============================================================================
# Image Operations
# =============================================================================

# Pull container image
container_pull() {
    local image="$1"
    
    [ -z "$CONTAINER_CMD" ] && container_init
    [ -z "$CONTAINER_CMD" ] && return 1
    
    log_info "Pulling image: $image"
    $CONTAINER_CMD pull "$image"
}

# Save container image to tar
container_save() {
    local image="$1"
    local output="${2:-$(cache_get_image "$image")}"
    
    [ -z "$CONTAINER_CMD" ] && container_init
    [ -z "$CONTAINER_CMD" ] && return 1
    
    log_info "Saving image: $image -> $output"
    $CONTAINER_CMD save "$image" -o "$output"
}

# Load container image from tar
container_load() {
    local tar_file="$1"
    
    [ -z "$CONTAINER_CMD" ] && container_init
    [ -z "$CONTAINER_CMD" ] && return 1
    
    if [ -f "$tar_file" ]; then
        log_info "Loading image: $tar_file"
        $CONTAINER_CMD load -i "$tar_file"
    else
        log_error "Image file not found: $tar_file"
        return 1
    fi
}

# Check if image exists locally
container_has_image() {
    local image="$1"
    
    [ -z "$CONTAINER_CMD" ] && container_init
    [ -z "$CONTAINER_CMD" ] && return 1
    
    $CONTAINER_CMD image exists "$image" 2>/dev/null || \
    $CONTAINER_CMD images -q "$image" 2>/dev/null | grep -q .
}

# =============================================================================
# Cache Integration
# =============================================================================

# Pull and cache image
container_pull_and_cache() {
    local image="$1"
    local cached=$(cache_get_image "$image")
    
    if cache_has_image "$image"; then
        local size=$(file_size_human "$cached")
        log_success "Using cached image: $image ($size)"
        return 0
    fi
    
    [ -z "$CONTAINER_CMD" ] && container_init
    [ -z "$CONTAINER_CMD" ] && return 1
    
    log_info "Pulling and caching: $image"
    if container_pull "$image"; then
        container_save "$image" "$cached"
        log_success "Image cached: $cached"
        return 0
    else
        log_error "Failed to pull: $image"
        return 1
    fi
}

# Load all cached images
container_load_all_cached() {
    [ -z "$CONTAINER_CMD" ] && container_init
    [ -z "$CONTAINER_CMD" ] && return 1
    
    local loaded=0
    for tar in $(cache_list_images); do
        if [ -f "$tar" ]; then
            container_load "$tar" && loaded=$((loaded + 1))
        fi
    done
    
    log_success "Loaded $loaded cached images"
    return 0
}

# =============================================================================
# Container Status
# =============================================================================

# List local images
container_list_images() {
    [ -z "$CONTAINER_CMD" ] && container_init
    [ -z "$CONTAINER_CMD" ] && return 1
    
    $CONTAINER_CMD images --format "{{.Repository}}:{{.Tag}} ({{.Size}})"
}

# List running containers
container_list_running() {
    [ -z "$CONTAINER_CMD" ] && container_init
    [ -z "$CONTAINER_CMD" ] && return 1
    
    $CONTAINER_CMD ps --format "{{.Names}}: {{.Status}}"
}

# Check if container is running
container_is_running() {
    local name="$1"
    
    [ -z "$CONTAINER_CMD" ] && container_init
    [ -z "$CONTAINER_CMD" ] && return 1
    
    $CONTAINER_CMD ps --format "{{.Names}}" | grep -q "^${name}$"
}

# =============================================================================
# Predefined Images
# =============================================================================

# Default images for LLM Station
LLM_STATION_IMAGES=(
    "ollama/ollama:rocm"
)

if [ "${ENABLE_OPENWEBUI:-true}" = "true" ]; then
    LLM_STATION_IMAGES+=("ghcr.io/open-webui/open-webui:main")
fi

# Pull and cache all LLM Station images
container_prepare_llm_station() {
    log_info "Preparing LLM Station container images..."
    
    local success=0
    local failed=0
    
    for image in "${LLM_STATION_IMAGES[@]}"; do
        if container_pull_and_cache "$image"; then
            success=$((success + 1))
        else
            failed=$((failed + 1))
        fi
    done
    
    log_info "Images prepared: $success success, $failed failed"
    [ $failed -eq 0 ]
}
