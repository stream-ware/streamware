#!/bin/bash
# Streamware App Creation Examples
# Create web and desktop apps in seconds!

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "======================================================================"
echo "STREAMWARE APP CREATION EXAMPLES"
echo "======================================================================"
echo ""

# Example 1: Create Flask Web App
echo -e "${BLUE}=== Example 1: Flask Web App ===${NC}"
echo ""
echo "# Create Flask app"
echo "sq webapp create --framework flask --name myapp --output ./myapp"
echo ""
echo "# Serve it"
echo "cd myapp && sq webapp serve --framework flask --port 5000"
echo ""

# Example 2: Create FastAPI App
echo -e "${BLUE}=== Example 2: FastAPI App ===${NC}"
echo ""
echo "# Create FastAPI app"
echo "sq webapp create --framework fastapi --name api --output ./api"
echo ""
echo "# Serve with auto-reload"
echo "cd api && sq webapp serve --framework fastapi --port 8000"
echo ""

# Example 3: Create Streamlit Dashboard
echo -e "${BLUE}=== Example 3: Streamlit Dashboard ===${NC}"
echo ""
echo "# Create Streamlit app"
echo "sq webapp create --framework streamlit --name dashboard --output ./dashboard"
echo ""
echo "# Run dashboard"
echo "cd dashboard && sq webapp serve --framework streamlit"
echo ""

# Example 4: Create Gradio ML Interface
echo -e "${BLUE}=== Example 4: Gradio ML Interface ===${NC}"
echo ""
echo "# Create Gradio app"
echo "sq webapp create --framework gradio --name ml-demo --output ./ml-demo"
echo ""
echo "# Serve"
echo "cd ml-demo && python app.py"
echo ""

# Example 5: Create Tkinter Desktop App
echo -e "${BLUE}=== Example 5: Tkinter Desktop App ===${NC}"
echo ""
echo "# Create desktop app (Tkinter is built-in!)"
echo "sq desktop create --framework tkinter --name calculator --output ./calculator"
echo ""
echo "# Run"
echo "cd calculator && python app.py"
echo ""

# Example 6: Create PyQt Desktop App
echo -e "${BLUE}=== Example 6: PyQt Desktop App ===${NC}"
echo ""
echo "# Create PyQt app (auto-installs PyQt6)"
echo "sq desktop create --framework pyqt --name notepad --output ./notepad"
echo ""
echo "# Run"
echo "cd notepad && python app.py"
echo ""

# Example 7: One-Liner Web App
echo -e "${CYAN}=== One-Liner Examples ===${NC}"
echo ""
echo "# Flask"
echo "sq webapp create --framework flask --name blog && cd blog && sq webapp serve"
echo ""
echo "# FastAPI"
echo "sq webapp create --framework fastapi --name api && cd api && sq webapp serve"
echo ""
echo "# Streamlit"
echo "sq webapp create --framework streamlit --name viz && cd viz && sq webapp serve"
echo ""

# Example 8: AI-Powered App Creation
echo -e "${CYAN}=== AI-Powered Creation ===${NC}"
echo ""
echo "# Use LLM to generate the command"
echo 'sq llm "create a web API with FastAPI" --to-sq'
echo "# Output: sq webapp create --framework fastapi --name api"
echo ""
echo "# Execute it"
echo 'sq llm "create a web API with FastAPI" --to-sq --execute'
echo ""

# Example 9: Complete Workflow
echo -e "${CYAN}=== Complete Workflow ===${NC}"
echo ""
cat << 'EOF'
# 1. Create app
sq webapp create --framework flask --name myapp

# 2. Navigate
cd myapp

# 3. Run (deps auto-installed!)
python app.py

# 4. Test
curl http://localhost:5000

# 5. Build Docker image
sq webapp build

# 6. Deploy to Kubernetes
docker build -t myapp:latest .
docker push registry/myapp:latest
sq deploy k8s --apply --file deployment.yaml

# Done! 🚀
EOF

echo ""
echo "======================================================================"
echo "DEMO COMPLETE!"
echo "======================================================================"
echo ""
echo -e "${GREEN}✓ Web app creation (Flask, FastAPI, Streamlit, Gradio, Dash)${NC}"
echo -e "${GREEN}✓ Desktop app creation (Tkinter, PyQt, Kivy)${NC}"
echo -e "${GREEN}✓ Auto-installation of dependencies${NC}"
echo -e "${GREEN}✓ One-liner creation and serving${NC}"
echo -e "${GREEN}✓ AI-powered app generation${NC}"
echo ""
echo "Try it yourself:"
echo "  sq webapp create --framework flask --name myapp"
echo "  cd myapp && python app.py"
echo ""
