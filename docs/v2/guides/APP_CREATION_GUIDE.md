# App Creation Guide - Streamware 0.2.0

## 🎯 Overview

Streamware now makes it incredibly easy to create web and desktop applications with auto-dependency installation!

## 🌐 Web Applications

### Supported Frameworks
- **Flask** - Classic Python web framework
- **FastAPI** - Modern async API framework
- **Streamlit** - Data apps and dashboards
- **Gradio** - ML interfaces
- **Dash** - Plotly dashboards

### Create Web App

```bash
# Flask (auto-installs flask and flask-cors)
sq webapp create --framework flask --name myapp

# FastAPI (auto-installs fastapi and uvicorn)
sq webapp create --framework fastapi --name api

# Streamlit (auto-installs streamlit)
sq webapp create --framework streamlit --name dashboard
```

### Serve Web App

```bash
cd myapp
sq webapp serve --framework flask --port 5000
# Or directly:
python app.py
```

### One-Liner

```bash
sq webapp create --framework flask --name blog && cd blog && python app.py
```

## 🖥️ Desktop Applications

### Supported Frameworks
- **Tkinter** - Built-in, no installation needed
- **PyQt** - Professional GUI (auto-installs PyQt6)
- **Kivy** - Cross-platform (auto-installs kivy)

### Create Desktop App

```bash
# Tkinter (no deps needed!)
sq desktop create --framework tkinter --name calculator

# PyQt (auto-installs PyQt6)
sq desktop create --framework pyqt --name notepad

# Kivy (auto-installs kivy)
sq desktop create --framework kivy --name game
```

### Run Desktop App

```bash
cd calculator
python app.py
```

### Build Executable

```bash
sq desktop build --name calculator
# Creates dist/calculator executable
```

## 🔧 Auto-Installation

**All dependencies install automatically!**

When you create an app, Streamware:
1. ✅ Checks if framework is installed
2. ✅ Installs missing packages automatically
3. ✅ Generates complete app code
4. ✅ Creates requirements.txt
5. ✅ Adds README with instructions

**No manual `pip install` needed!**

## 🤖 AI-Powered Creation

Use LLM to generate app commands:

```bash
# Generate command
sq llm "create a web API with FastAPI" --to-sq
# Output: sq webapp create --framework fastapi --name api

# Execute directly
sq llm "create a web dashboard with Streamlit" --to-sq --execute
```

## 📊 Complete Workflow Examples

### Web App Workflow

```bash
# 1. Create
sq webapp create --framework flask --name blog --output ./blog

# 2. Navigate
cd blog

# 3. Run (deps auto-installed!)
python app.py

# 4. Test
curl http://localhost:5000

# 5. Deploy
sq deploy k8s --apply --file deployment.yaml
```

### Desktop App Workflow

```bash
# 1. Create
sq desktop create --framework tkinter --name todo --output ./todo

# 2. Navigate
cd todo

# 3. Run
python app.py

# 4. Build executable
sq desktop build --name todo

# 5. Distribute
./dist/todo
```

## 🎨 Generated App Features

### Flask App Includes:
- ✅ REST API endpoints
- ✅ CORS enabled
- ✅ JSON responses
- ✅ Error handling
- ✅ Ready to extend

### FastAPI App Includes:
- ✅ Async endpoints
- ✅ Pydantic models
- ✅ Auto docs (Swagger)
- ✅ CORS middleware
- ✅ Type hints

### Streamlit App Includes:
- ✅ Interactive widgets
- ✅ Sidebar navigation
- ✅ Input/output sections
- ✅ Beautiful UI
- ✅ Hot reload

### Desktop App Includes:
- ✅ Main window
- ✅ Input fields
- ✅ Buttons with actions
- ✅ Output display
- ✅ Event handling

## 🚀 Quick Reference

```bash
# Web Apps
sq webapp create --framework flask --name myapp
sq webapp create --framework fastapi --name api
sq webapp create --framework streamlit --name dashboard
sq webapp create --framework gradio --name ml-demo
sq webapp create --framework dash --name viz

# Desktop Apps
sq desktop create --framework tkinter --name app
sq desktop create --framework pyqt --name gui
sq desktop create --framework kivy --name mobile

# Serve
sq webapp serve --framework flask --port 5000
sq webapp serve --framework fastapi --port 8000

# Build
sq desktop build --name myapp
```

## 💡 Tips

### 1. Choose the Right Framework

**Web:**
- **Flask** - Traditional web apps
- **FastAPI** - Modern APIs
- **Streamlit** - Data dashboards
- **Gradio** - ML demos
- **Dash** - Complex visualizations

**Desktop:**
- **Tkinter** - Simple GUIs (fastest start)
- **PyQt** - Professional apps
- **Kivy** - Mobile-ready

### 2. Use AI for Custom Apps

```bash
# Describe what you want
sq llm "create a REST API for managing tasks with FastAPI" --to-sq --execute
```

### 3. Deploy Anywhere

```bash
# Docker
sq webapp build  # Creates Dockerfile
docker build -t myapp .

# Kubernetes
sq deploy k8s --apply --file deployment.yaml

# Cloud
# Use generated Dockerfile with any cloud platform
```

## 🎓 Examples

See `examples/app_creation_examples.sh` for complete examples!

```bash
bash examples/app_creation_examples.sh
```

---

**Create apps in seconds with Streamware! 🚀**
