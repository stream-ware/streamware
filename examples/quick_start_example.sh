#!/bin/bash
# Streamware 0.2.0 - Quick Start Example
# Demonstrates new auto-install, templates, and registry features

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "======================================================================"
echo "STREAMWARE 0.2.0 - QUICK START DEMO"
echo "======================================================================"
echo ""

# 1. Check registry
echo -e "${BLUE}→ Step 1: Check Registry${NC}"
sq registry list --type component
echo ""

# 2. Lookup component
echo -e "${BLUE}→ Step 2: Lookup Video Component${NC}"
sq registry lookup --type component --name video
echo ""

# 3. List templates
echo -e "${BLUE}→ Step 3: List Templates${NC}"
sq template list
echo ""

# 4. Check dependencies
echo -e "${BLUE}→ Step 4: Check Dependencies${NC}"
sq setup check --packages opencv-python,numpy
echo ""

# 5. Auto-install (commented - uncomment to actually install)
echo -e "${BLUE}→ Step 5: Auto-Install (dry-run)${NC}"
echo "Command: sq setup all --component video"
echo "(Commented out - remove # to install)"
# sq setup all --component video
echo ""

# 6. Generate project
echo -e "${BLUE}→ Step 6: Generate Project${NC}"
echo "Command: sq template generate --name video-captioning --output ./my-video-project"
echo "(Creates project with all files and auto-installs deps)"
# sq template generate --name video-captioning --output ./my-video-project
echo ""

# 7. Example workflow
echo -e "${CYAN}=== Example Workflow ===${NC}"
echo ""
echo -e "${GREEN}# 1. Create new project from template${NC}"
echo "sq template generate --name video-captioning --output my-project"
echo ""
echo -e "${GREEN}# 2. Navigate to project${NC}"
echo "cd my-project"
echo ""
echo -e "${GREEN}# 3. Dependencies are auto-installed!${NC}"
echo "python video_captioning_complete.py"
echo ""
echo -e "${GREEN}# 4. Open browser${NC}"
echo "open http://localhost:8080"
echo ""

# 8. LLM-powered workflow
echo -e "${CYAN}=== LLM-Powered Workflow ===${NC}"
echo ""
echo -e "${GREEN}# Install Ollama model${NC}"
echo "sq setup ollama --model qwen2.5:14b"
echo ""
echo -e "${GREEN}# Generate command from natural language${NC}"
echo 'sq llm "upload file to production server" --to-sq'
echo ""
echo -e "${GREEN}# Execute generated command${NC}"
echo 'sq llm "backup database and send to slack" --to-sq --execute'
echo ""

# 9. Deployment workflow
echo -e "${CYAN}=== Deployment Workflow ===${NC}"
echo ""
echo -e "${GREEN}# Deploy to Kubernetes${NC}"
echo "sq deploy k8s --apply --file deployment.yaml --namespace production"
echo ""
echo -e "${GREEN}# Scale deployment${NC}"
echo "sq deploy k8s --scale 5 --name myapp"
echo ""
echo -e "${GREEN}# Check status${NC}"
echo "sq deploy k8s --status --namespace production"
echo ""

# 10. Complete example
echo -e "${CYAN}=== Complete AI-Powered Example ===${NC}"
echo ""
cat << 'EOF'
# 1. Setup environment
sq setup all --component video
sq setup ollama --model llama3.2

# 2. Generate project
sq template generate --name video-captioning --output my-app
cd my-app

# 3. Customize with LLM
sq llm "modify config to use rtsp://camera.local/stream" --to-bash --execute

# 4. Run application
python video_captioning_complete.py &

# 5. Deploy to Kubernetes
sq deploy k8s --apply --file k8s/deployment.yaml

# 6. Monitor
sq deploy k8s --logs --name myapp

# All in ~6 commands! 🚀
EOF

echo ""
echo "======================================================================"
echo "DEMO COMPLETE!"
echo "======================================================================"
echo ""
echo -e "${GREEN}✓ Checked registry${NC}"
echo -e "${GREEN}✓ Looked up components${NC}"
echo -e "${GREEN}✓ Listed templates${NC}"
echo -e "${GREEN}✓ Checked dependencies${NC}"
echo ""
echo "Try it yourself:"
echo "  sq template generate --name video-captioning"
echo "  sq setup all --component video"
echo "  sq llm 'your request' --to-sq"
echo ""
