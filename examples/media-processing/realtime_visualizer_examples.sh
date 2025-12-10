#!/bin/bash
# Real-time Visualizer Examples
# Motion detection with SVG overlays and DSL metadata streaming

echo "=== Real-time Visualizer Examples ==="
echo ""

# Replace with your camera URL
CAMERA_URL="rtsp://admin:password@192.168.1.100:554/stream"

# ============================================================================
# Basic Usage
# ============================================================================

echo "# 1. Basic WebSocket mode (default)"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080"
echo ""

echo "# 2. Open in browser"
echo "# http://localhost:8080"
echo ""

# ============================================================================
# Video Modes
# ============================================================================

echo "# 3. Metadata-only mode (high FPS, low bandwidth)"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080 --video-mode meta --fps 10"
echo ""

echo "# 4. HLS mode (stable streaming)"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080 --video-mode hls"
echo ""

echo "# 5. WebRTC mode (experimental, ultra-low latency)"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080 --video-mode webrtc"
echo ""

# ============================================================================
# Transport Options
# ============================================================================

echo "# 6. UDP transport (lower latency, may drop frames)"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080 --transport udp"
echo ""

echo "# 7. TCP transport (stable, default)"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080 --transport tcp"
echo ""

# ============================================================================
# Capture Backends
# ============================================================================

echo "# 8. PyAV backend (direct API, no subprocess)"
echo "# Requires: pip install av"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080 --backend pyav"
echo ""

echo "# 9. GStreamer backend (fastest, requires OpenCV with GStreamer)"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080 --backend gstreamer"
echo ""

echo "# 10. OpenCV/ffmpeg backend (default, most compatible)"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080 --backend opencv"
echo ""

# ============================================================================
# Lowest Latency Configuration
# ============================================================================

echo "# 11. Lowest latency setup"
echo "sq visualize \\"
echo "  --url \"$CAMERA_URL\" \\"
echo "  --port 8080 \\"
echo "  --video-mode meta \\"
echo "  --fps 15 \\"
echo "  --transport udp \\"
echo "  --backend pyav \\"
echo "  --width 320 \\"
echo "  --height 240"
echo ""

# ============================================================================
# Fast Mode
# ============================================================================

echo "# 12. Fast mode (auto-optimized settings)"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080 --fast"
echo ""

# ============================================================================
# Resolution Options
# ============================================================================

echo "# 13. Low resolution (faster processing)"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080 --width 320 --height 240"
echo ""

echo "# 14. High resolution (more detail)"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080 --width 640 --height 480"
echo ""

# ============================================================================
# Multiple Cameras
# ============================================================================

echo "# 15. Multiple cameras on different ports"
echo "sq visualize --url \"rtsp://camera1/stream\" --port 8081 &"
echo "sq visualize --url \"rtsp://camera2/stream\" --port 8082 &"
echo "sq visualize --url \"rtsp://camera3/stream\" --port 8083 &"
echo ""

# ============================================================================
# MQTT Integration
# ============================================================================

echo "# 16. Publish DSL to MQTT broker"
echo "sq mqtt --url \"$CAMERA_URL\" --broker localhost"
echo ""

echo "# 17. MQTT with custom topic"
echo "sq mqtt --url \"$CAMERA_URL\" --broker localhost --topic home/camera/front"
echo ""

echo "# 18. MQTT with authentication"
echo "sq mqtt --url \"$CAMERA_URL\" --broker mqtt.example.com --username user --password secret"
echo ""

echo "# 19. MQTT high sensitivity (low threshold)"
echo "sq mqtt --url \"$CAMERA_URL\" --broker localhost --threshold 0.5 --fps 10"
echo ""

# ============================================================================
# Subscribe to MQTT events
# ============================================================================

echo "# 20. Subscribe to all DSL events"
echo "mosquitto_sub -h localhost -t 'streamware/dsl/#' -v"
echo ""

echo "# 21. Subscribe to motion events only"
echo "mosquitto_sub -h localhost -t 'streamware/dsl/events'"
echo ""

echo "# 22. Subscribe to motion level"
echo "mosquitto_sub -h localhost -t 'streamware/dsl/motion'"
echo ""

# ============================================================================
# Combined Examples
# ============================================================================

echo "# 23. Visualizer + MQTT simultaneously"
echo "sq visualize --url \"$CAMERA_URL\" --port 8080 &"
echo "sq mqtt --url \"$CAMERA_URL\" --broker localhost &"
echo ""

echo "# 24. Production setup with all optimizations"
echo "sq visualize \\"
echo "  --url \"$CAMERA_URL\" \\"
echo "  --port 8080 \\"
echo "  --video-mode meta \\"
echo "  --fps 10 \\"
echo "  --transport udp \\"
echo "  --backend pyav \\"
echo "  --width 320 \\"
echo "  --height 240 &"
echo ""
echo "sq mqtt \\"
echo "  --url \"$CAMERA_URL\" \\"
echo "  --broker mqtt.local \\"
echo "  --topic security/cameras/front \\"
echo "  --threshold 5.0 \\"
echo "  --fps 5 &"
echo ""

echo "=== End of Examples ==="
