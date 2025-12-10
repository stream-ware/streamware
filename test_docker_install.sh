#!/bin/bash
set -e

echo "🐳 Building Streamware test image..."
docker build -f Dockerfile.test -t streamware-test .

echo "✅ Build successful!"
echo "🏃 Running verification container..."
docker run --rm streamware-test

echo "🎉 All tests passed! Package is valid."
