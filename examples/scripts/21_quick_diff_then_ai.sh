#!/bin/bash
# =============================================================================
# Two-Stage Detection: Quick Diff → AI Analysis
# Fast pixel check first, then AI only if changes detected
# =============================================================================

source "$(dirname "$0")/common.sh"

print_header "⚡ Two-Stage Detection"

CAMERA_URL="${1:-$CAMERA_URL}"
ensure_camera_url

setup_dirs

print_step "Stage 1: Quick Pixel Diff (No AI)"
echo "Fast check for any motion..."
echo ""

# Stage 1: Quick watch without AI
QUICK_RESULT=$(sq smart watch \
    --url "$CAMERA_URL" \
    --min-interval 0.5 \
    --max-interval 2 \
    --threshold 20 \
    --duration 15 \
    --no-ai \
    --json 2>/dev/null)

CHANGES=$(echo "$QUICK_RESULT" | jq -r '.frames_with_changes // 0')
CAPTURED=$(echo "$QUICK_RESULT" | jq -r '.frames_captured // 0')

echo "Captured: $CAPTURED frames"
echo "Changes detected: $CHANGES"
echo ""

if [ "$CHANGES" -eq 0 ]; then
    print_success "No motion detected. Skipping AI analysis."
    exit 0
fi

print_step "Stage 2: AI Analysis on Changed Frames"
echo "Motion detected! Running detailed AI analysis..."
echo ""

# Stage 2: Full analysis with AI
sq smart monitor \
    --url "$CAMERA_URL" \
    --min-interval 2 \
    --max-interval 5 \
    --threshold 20 \
    --focus "$FOCUS" \
    --duration 30 \
    --file "$REPORTS_DIR/two_stage_$(get_file_timestamp).html" \
    --yaml

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Two-Stage Benefits:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. FASTER INITIAL CHECK"
echo "   Pixel diff is instant (no AI delay)"
echo ""
echo "2. SAVES RESOURCES"
echo "   AI only runs when motion detected"
echo "   Perfect for mostly-static cameras"
echo ""
echo "3. EXAMPLE USE CASE"
echo "   Check 10 cameras quickly with Stage 1"
echo "   Only run expensive AI on cameras with motion"
echo ""
