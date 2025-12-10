#!/bin/bash
set -e

echo "🚀 Starting Cross-Platform Installation Tests..."

# Build Ubuntu target
echo "---------------------------------------------------"
echo "📦 Testing Ubuntu/Debian..."
docker build -f Dockerfile.cross_platform --target ubuntu_test .
echo "✅ Ubuntu test passed"

# Build Fedora target
echo "---------------------------------------------------"
echo "📦 Testing Fedora..."
docker build -f Dockerfile.cross_platform --target fedora_test .
echo "✅ Fedora test passed"

# Build Alpine target
echo "---------------------------------------------------"
echo "📦 Testing Alpine Linux..."
docker build -f Dockerfile.cross_platform --target alpine_test .
echo "✅ Alpine test passed"

echo "---------------------------------------------------"
echo "🎉 All cross-platform tests passed successfully!"
