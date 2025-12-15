#!/bin/bash
# =============================================================================
# Test Runner for USB/ISO Builder Libraries
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(dirname "$SCRIPT_DIR")/lib"
CACHE_DIR="${CACHE_DIR:-$(dirname "$SCRIPT_DIR")/cache}"

mkdir -p "$CACHE_DIR/tmp"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test assertion functions
assert_equals() {
    local expected="$1"
    local actual="$2"
    local msg="${3:-}"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    
    if [ "$expected" = "$actual" ]; then
        echo -e "${GREEN}✓${NC} $msg"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $msg"
        echo "  Expected: $expected"
        echo "  Actual:   $actual"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

assert_true() {
    local condition="$1"
    local msg="${2:-}"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    
    if eval "$condition"; then
        echo -e "${GREEN}✓${NC} $msg"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $msg"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

assert_file_exists() {
    local file="$1"
    local msg="${2:-File exists: $file}"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $msg"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $msg"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

assert_command_exists() {
    local cmd="$1"
    local msg="${2:-Command exists: $cmd}"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    
    if command -v "$cmd" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $msg"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${YELLOW}⚠${NC} $msg (skipped - not installed)"
        return 0  # Don't fail for missing optional commands
    fi
}

# =============================================================================
# Test: common.sh
# =============================================================================

test_common() {
    echo ""
    echo "=== Testing lib/common.sh ==="
    
    source "$LIB_DIR/common.sh"
    
    # Test logging functions exist
    assert_true "type log_info &>/dev/null" "log_info function exists"
    assert_true "type log_success &>/dev/null" "log_success function exists"
    assert_true "type log_warn &>/dev/null" "log_warn function exists"
    assert_true "type log_error &>/dev/null" "log_error function exists"
    
    # Test command_exists
    assert_true "command_exists bash" "command_exists detects bash"
    assert_true "! command_exists nonexistent_command_xyz" "command_exists returns false for missing"
    
    # Test ensure_dir
    local test_dir=$(mktemp -d -p "$CACHE_DIR/tmp" usb-builder-test-XXXXXX)
    ensure_dir "$test_dir"
    assert_true "[ -d '$test_dir' ]" "ensure_dir creates directory"
    rm -rf "$test_dir"
    
    # Test file_size
    local test_file=$(mktemp -p "$CACHE_DIR/tmp" usb-builder-test-file-XXXXXX)
    echo "test content" > "$test_file"
    local size=$(file_size "$test_file")
    assert_true "[ '$size' -gt 0 ]" "file_size returns size > 0"
    rm -f "$test_file"
    
    # Test find_free_port
    local port=$(find_free_port 59999)
    assert_true "[ -n '$port' ]" "find_free_port returns a port"
    
    # Test detect_package_manager
    local pm=$(detect_package_manager)
    assert_true "[ -n '$pm' ]" "detect_package_manager returns value"
}

# =============================================================================
# Test: cache.sh
# =============================================================================

test_cache() {
    echo ""
    echo "=== Testing lib/cache.sh ==="
    
    source "$LIB_DIR/cache.sh"
    
    # Test cache functions exist
    assert_true "type cache_init &>/dev/null" "cache_init function exists"
    assert_true "type cache_has_iso &>/dev/null" "cache_has_iso function exists"
    assert_true "type cache_get_iso &>/dev/null" "cache_get_iso function exists"
    assert_true "type cache_status &>/dev/null" "cache_status function exists"
    
    # Test cache_get_iso returns path
    local iso_path=$(cache_get_iso "test.iso")
    assert_true "[ -n '$iso_path' ]" "cache_get_iso returns path"
    
    # Test cache_has_iso returns false for missing
    assert_true "! cache_has_iso 'nonexistent.iso'" "cache_has_iso returns false for missing"
}

# =============================================================================
# Test: container.sh
# =============================================================================

test_container() {
    echo ""
    echo "=== Testing lib/container.sh ==="
    
    source "$LIB_DIR/container.sh"
    
    # Test container functions exist
    assert_true "type detect_container_runtime &>/dev/null" "detect_container_runtime function exists"
    assert_true "type container_init &>/dev/null" "container_init function exists"
    
    # Test detect_container_runtime
    local runtime=$(detect_container_runtime)
    if [ -n "$runtime" ]; then
        assert_true "[ '$runtime' = 'podman' ] || [ '$runtime' = 'docker' ]" "detect_container_runtime returns podman or docker"
    else
        echo -e "${YELLOW}⚠${NC} No container runtime installed (skipping)"
    fi
}

# =============================================================================
# Test: config.sh
# =============================================================================

test_config() {
    echo ""
    echo "=== Testing config.sh ==="
    
    source "$(dirname "$LIB_DIR")/config.sh"
    
    # Test config variables exist
    assert_true "[ -n '$ISO_NAME' ]" "ISO_NAME is set"
    assert_true "[ -n '$DISTRO' ]" "DISTRO is set"
    assert_true "[ -n '$OUTPUT_DIR' ]" "OUTPUT_DIR is set"
    assert_true "[ -n '$CACHE_DIR' ]" "CACHE_DIR is set"
    
    # Test get functions
    local url=$(get_base_iso_url)
    assert_true "[ -n '$url' ]" "get_base_iso_url returns URL"
    
    local name=$(get_base_iso_name)
    assert_true "[ -n '$name' ]" "get_base_iso_name returns name"
    
    # Test validate_config
    assert_true "validate_config" "validate_config passes"
}

# =============================================================================
# Test: boot.sh
# =============================================================================

test_boot() {
    echo ""
    echo "=== Testing lib/boot.sh ==="
    
    source "$LIB_DIR/boot.sh"
    
    # Test boot functions exist
    assert_true "type generate_first_boot_script &>/dev/null" "generate_first_boot_script function exists"
    assert_true "type generate_autostart_desktop &>/dev/null" "generate_autostart_desktop function exists"
    assert_true "type generate_autorun_script &>/dev/null" "generate_autorun_script function exists"
    
    # Test script generation
    local test_script=$(mktemp -p "$CACHE_DIR/tmp" usb-builder-test-firstboot-XXXXXX)
    generate_first_boot_script "$test_script"
    assert_file_exists "$test_script" "generate_first_boot_script creates file"
    assert_true "[ -x '$test_script' ]" "generated script is executable"
    rm -f "$test_script"
}

# =============================================================================
# Run All Tests
# =============================================================================

echo "=========================================="
echo "USB/ISO Builder Library Tests"
echo "=========================================="

# Check library files exist
assert_file_exists "$LIB_DIR/common.sh" "lib/common.sh exists"
assert_file_exists "$LIB_DIR/cache.sh" "lib/cache.sh exists"
assert_file_exists "$LIB_DIR/container.sh" "lib/container.sh exists"
assert_file_exists "$LIB_DIR/boot.sh" "lib/boot.sh exists"
assert_file_exists "$(dirname "$LIB_DIR")/config.sh" "config.sh exists"

# Run test suites
test_common
test_cache
test_container
test_config
test_boot

# Summary
echo ""
echo "=========================================="
echo "Test Results"
echo "=========================================="
echo "Total:  $TESTS_RUN"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi
