#!/bin/bash
# Streamware Video Captioning - Installation Script
# Complete setup for video captioning system

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() {
    echo -e "${BLUE}→ $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

echo "======================================================================"
echo "STREAMWARE VIDEO CAPTIONING - INSTALLATION"
echo "======================================================================"
echo ""

# Check Python
info "Checking Python..."
if ! command -v python3 &> /dev/null; then
    error "Python 3 not found. Please install Python 3.8+"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
success "Python $PYTHON_VERSION found"
echo ""

# Check system dependencies
info "Checking system dependencies..."

# OpenCV system libs
if command -v apt-get &> /dev/null; then
    info "Detected Debian/Ubuntu"
    echo "Installing system packages..."
    sudo apt-get update
    sudo apt-get install -y \
        python3-opencv \
        ffmpeg \
        libopencv-dev \
        python3-dev \
        build-essential
elif command -v brew &> /dev/null; then
    info "Detected macOS"
    echo "Installing with Homebrew..."
    brew install opencv ffmpeg
else
    warn "Unknown system. Please install OpenCV and FFmpeg manually."
fi
echo ""

# Create virtual environment
info "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    success "Virtual environment created"
else
    success "Virtual environment already exists"
fi
echo ""

# Activate venv
info "Activating virtual environment..."
source venv/bin/activate
success "Virtual environment activated"
echo ""

# Upgrade pip
info "Upgrading pip..."
pip install --upgrade pip setuptools wheel
success "Pip upgraded"
echo ""

# Install Streamware
info "Installing Streamware..."
cd ../..
pip install -e .
cd projects/video-captioning
success "Streamware installed"
echo ""

# Install Python packages
info "Installing Python dependencies..."

# Core dependencies
pip install opencv-python numpy

# YOLO
info "Installing YOLO (Ultralytics)..."
pip install ultralytics

# Web server
info "Installing web server (Flask)..."
pip install flask flask-socketio python-socketio[client]

# LLM support (optional)
read -p "Install OpenAI support? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install openai
    success "OpenAI installed"
fi

read -p "Install Anthropic support? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install anthropic
    success "Anthropic installed"
fi

success "All Python packages installed"
echo ""

# Install Ollama (optional)
info "Ollama setup (FREE local LLM)..."
read -p "Install Ollama? (recommended, y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v ollama &> /dev/null; then
        success "Ollama already installed"
    else
        info "Installing Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
        success "Ollama installed"
    fi
    
    info "Pulling Llama 3.2 model..."
    ollama pull llama3.2
    success "Model downloaded"
fi
echo ""

# Download YOLO model
info "Downloading YOLO model..."
python3 << 'EOF'
from ultralytics import YOLO
print("Downloading YOLOv8n model...")
model = YOLO('yolov8n.pt')
print("✓ Model downloaded")
EOF
success "YOLO model ready"
echo ""

# Create test video (optional)
info "Setting up test environment..."
mkdir -p test_data logs

# Download test video
if [ ! -f "test_data/test_video.mp4" ]; then
    read -p "Download test video? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Downloading test video..."
        wget -q https://sample-videos.com/video123/mp4/480/big_buck_bunny_480p_1mb.mp4 \
             -O test_data/test_video.mp4 || \
        curl -sL https://sample-videos.com/video123/mp4/480/big_buck_bunny_480p_1mb.mp4 \
             -o test_data/test_video.mp4
        success "Test video downloaded"
    fi
fi
echo ""

# Configuration
info "Creating configuration..."
cat > config.env << 'EOF'
# Streamware Video Captioning Configuration

# Video source (edit this)
export RTSP_URL="rtsp://localhost:8554/stream"
# Use webcam: RTSP_URL="0"
# Use file: RTSP_URL="test_data/test_video.mp4"

# LLM provider
export LLM_PROVIDER="ollama"
export LLM_MODEL="llama3.2:latest"

# Optional: OpenAI
# export OPENAI_API_KEY="sk-..."

# Optional: Anthropic
# export ANTHROPIC_API_KEY="sk-ant-..."

# Web server
export WEB_PORT=8080
EOF
success "Configuration created (config.env)"
echo ""

# Create run script
info "Creating run script..."
cat > run.sh << 'EOF'
#!/bin/bash
# Run Streamware Video Captioning

# Load config
source config.env

# Activate venv
source venv/bin/activate

# Run
python video_captioning_complete.py
EOF
chmod +x run.sh
success "Run script created (./run.sh)"
echo ""

# Create Docker files
info "Creating Docker files..."

cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-opencv \
    ffmpeg \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY video_captioning_complete.py .

# Expose port
EXPOSE 8080

# Run
CMD ["python", "video_captioning_complete.py"]
EOF

cat > requirements.txt << 'EOF'
opencv-python>=4.8.0
numpy>=1.24.0
ultralytics>=8.0.0
flask>=3.0.0
flask-socketio>=5.3.0
python-socketio[client]>=5.10.0
EOF

success "Docker files created"
echo ""

# Summary
echo "======================================================================"
echo "INSTALLATION COMPLETE!"
echo "======================================================================"
echo ""
success "Everything is ready to go!"
echo ""
echo "📝 Quick Start:"
echo ""
echo "1. Edit configuration:"
echo "   nano config.env"
echo ""
echo "2. Start the system:"
echo "   ./run.sh"
echo ""
echo "3. Open browser:"
echo "   http://localhost:8080"
echo ""
echo "======================================================================"
echo "OPTIONAL: Setup RTSP Test Stream"
echo "======================================================================"
echo ""
echo "Start RTSP server (in another terminal):"
echo "  docker run -d -p 8554:8554 --name rtsp-server aler9/rtsp-simple-server"
echo ""
echo "Stream test video:"
echo "  ffmpeg -re -stream_loop -1 -i test_data/test_video.mp4 \\"
echo "    -f rtsp rtsp://localhost:8554/stream"
echo ""
echo "Or use webcam:"
echo "  Edit config.env: RTSP_URL=\"0\""
echo ""
echo "======================================================================"
echo "DOCKER DEPLOYMENT"
echo "======================================================================"
echo ""
echo "Build image:"
echo "  docker build -t streamware-video-captioning ."
echo ""
echo "Run container:"
echo "  docker run -d -p 8080:8080 --name video-captioning \\"
echo "    -e RTSP_URL=\"rtsp://your-camera/stream\" \\"
echo "    streamware-video-captioning"
echo ""
echo "======================================================================"
echo "DOCUMENTATION"
echo "======================================================================"
echo ""
echo "Full documentation: README.md"
echo "Streamware docs: ../../docs/"
echo ""
echo "For support: info@softreck.com"
echo ""
echo "Happy video captioning! 🎥✨"
echo ""
