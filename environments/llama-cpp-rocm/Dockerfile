# =============================================================================
# Dockerfile for llama.cpp with ROCm support for AMD Radeon 780M (RDNA3)
# Optimized for UM790 Pro
# =============================================================================

FROM rocm/dev-ubuntu-22.04:6.0.2

LABEL maintainer="streamware"
LABEL description="llama.cpp with ROCm for AMD Radeon 780M"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# ROCm environment for RDNA3 (gfx1103)
ENV ROCM_PATH=/opt/rocm
ENV PATH=$PATH:$ROCM_PATH/bin
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$ROCM_PATH/lib
ENV HSA_OVERRIDE_GFX_VERSION=11.0.0
ENV HIP_VISIBLE_DEVICES=0

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    curl \
    python3 \
    python3-pip \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Clone and build llama.cpp with ROCm/HIP support
WORKDIR /app
RUN git clone https://github.com/ggerganov/llama.cpp.git && \
    cd llama.cpp && \
    cmake -B build \
        -DGGML_HIP=ON \
        -DAMDGPU_TARGETS="gfx1103" \
        -DCMAKE_BUILD_TYPE=Release \
        -DGGML_HIP_UMA=ON \
        -DLLAMA_CURL=ON && \
    cmake --build build --config Release -j$(nproc)

# Install Python dependencies for web server
RUN pip3 install --no-cache-dir \
    flask \
    flask-cors \
    requests \
    gradio

# Copy web interface
WORKDIR /app/llama.cpp

# Expose ports
EXPOSE 8080

# Create models directory
RUN mkdir -p /models

# Default command: run server
CMD ["./build/bin/llama-server", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "-m", "/models/model.gguf", \
     "-ngl", "99", \
     "--ctx-size", "4096"]
