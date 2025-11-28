"""
Web App Component for Streamware

Create web applications with popular frameworks in minutes.
Supports Flask, FastAPI, Streamlit, Gradio, and more.

# Menu:
- [Quick Start](#quick-start)
- [Frameworks](#frameworks)
- [Examples](#examples)
- [Deployment](#deployment)
"""

from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


@register("webapp")
@register("web")
class WebAppComponent(Component):
    """
    Web application generator and server
    
    Frameworks:
    - flask: Flask web framework
    - fastapi: FastAPI modern API framework
    - streamlit: Streamlit data apps
    - gradio: Gradio ML interfaces
    - dash: Plotly Dash dashboards
    
    Operations:
    - create: Create new web app
    - serve: Start development server
    - build: Build for production
    - deploy: Deploy to cloud
    
    URI Examples:
        webapp://create?framework=flask&name=myapp
        webapp://serve?port=8000&framework=fastapi
        webapp://create?framework=streamlit&name=dashboard
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    FRAMEWORKS = {
        "flask": {
            "packages": ["flask", "flask-cors"],
            "template": "flask_app.py",
            "port": 5000
        },
        "fastapi": {
            "packages": ["fastapi", "uvicorn[standard]"],
            "template": "fastapi_app.py",
            "port": 8000
        },
        "streamlit": {
            "packages": ["streamlit"],
            "template": "streamlit_app.py",
            "port": 8501
        },
        "gradio": {
            "packages": ["gradio"],
            "template": "gradio_app.py",
            "port": 7860
        },
        "dash": {
            "packages": ["dash", "plotly"],
            "template": "dash_app.py",
            "port": 8050
        }
    }
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "create"
        
        self.framework = uri.get_param("framework", "flask")
        self.name = uri.get_param("name", "myapp")
        self.port = int(uri.get_param("port", self.FRAMEWORKS.get(self.framework, {}).get("port", 8000)))
        self.host = uri.get_param("host", "0.0.0.0")
        self.auto_install = uri.get_param("auto_install", True)
        self.output_dir = uri.get_param("output", ".")
    
    def process(self, data: Any) -> Dict:
        """Process web app operation"""
        # Auto-install if needed
        if self.auto_install:
            self._ensure_dependencies()
        
        operations = {
            "create": self._create,
            "serve": self._serve,
            "build": self._build,
            "deploy": self._deploy,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _ensure_dependencies(self):
        """Ensure framework dependencies are installed"""
        if self.framework not in self.FRAMEWORKS:
            raise ComponentError(f"Unknown framework: {self.framework}")
        
        packages = self.FRAMEWORKS[self.framework]["packages"]
        
        for pkg in packages:
            try:
                __import__(pkg.split("[")[0].replace("-", "_"))
            except ImportError:
                logger.info(f"Installing {pkg}...")
                subprocess.run(
                    ["pip", "install", pkg],
                    check=True,
                    capture_output=True
                )
    
    def _create(self, data: Any) -> Dict:
        """Create new web app"""
        output_path = Path(self.output_dir) / self.name
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate app file based on framework
        app_content = self._generate_app_code()
        
        app_file = output_path / f"app.py"
        with open(app_file, 'w') as f:
            f.write(app_content)
        
        # Generate requirements.txt
        requirements = "\n".join(self.FRAMEWORKS[self.framework]["packages"])
        with open(output_path / "requirements.txt", 'w') as f:
            f.write(requirements)
        
        # Generate README
        readme = self._generate_readme()
        with open(output_path / "README.md", 'w') as f:
            f.write(readme)
        
        return {
            "success": True,
            "framework": self.framework,
            "name": self.name,
            "path": str(output_path),
            "files": ["app.py", "requirements.txt", "README.md"]
        }
    
    def _serve(self, data: Any) -> Dict:
        """Start development server"""
        # Change to app directory if it exists
        app_dir = Path(self.name)
        if app_dir.exists() and app_dir.is_dir():
            os.chdir(app_dir)
        
        if self.framework == "flask":
            os.environ["FLASK_APP"] = "app.py"
            subprocess.run(["flask", "run", "--host", self.host, "--port", str(self.port)])
        
        elif self.framework == "fastapi":
            subprocess.run(["uvicorn", "app:app", "--host", self.host, "--port", str(self.port), "--reload"])
        
        elif self.framework == "streamlit":
            subprocess.run(["streamlit", "run", "app.py", "--server.port", str(self.port)])
        
        elif self.framework == "gradio":
            # Gradio apps serve themselves
            subprocess.run(["python", "app.py"])
        
        elif self.framework == "dash":
            subprocess.run(["python", "app.py"])
        
        return {"success": True}
    
    def _build(self, data: Any) -> Dict:
        """Build for production"""
        # Create Dockerfile
        dockerfile = self._generate_dockerfile()
        with open("Dockerfile", 'w') as f:
            f.write(dockerfile)
        
        return {"success": True, "dockerfile": "Dockerfile"}
    
    def _deploy(self, data: Any) -> Dict:
        """Deploy to cloud"""
        # This would integrate with deploy component
        return {"success": True, "message": "Use sq deploy for deployment"}
    
    def _generate_app_code(self) -> str:
        """Generate app code based on framework"""
        if self.framework == "flask":
            return '''from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({"message": "Hello from Flask!", "app": "''' + self.name + '''"})

@app.route('/api/data', methods=['GET', 'POST'])
def data():
    if request.method == 'POST':
        data = request.json
        return jsonify({"received": data, "status": "success"})
    return jsonify({"data": "Sample data", "status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=''' + str(self.port) + ''', debug=True)
'''
        
        elif self.framework == "fastapi":
            return '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="''' + self.name + '''")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Item(BaseModel):
    name: str
    value: str

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!", "app": "''' + self.name + '''"}

@app.get("/api/data")
def get_data():
    return {"data": "Sample data", "status": "ok"}

@app.post("/api/data")
def post_data(item: Item):
    return {"received": item.dict(), "status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=''' + str(self.port) + ''')
'''
        
        elif self.framework == "streamlit":
            return '''import streamlit as st

st.set_page_config(page_title="''' + self.name + '''", page_icon="🚀")

st.title("🚀 ''' + self.name + '''")
st.write("Built with Streamlit and Streamware")

# Sidebar
st.sidebar.header("Options")
option = st.sidebar.selectbox("Choose option", ["Option 1", "Option 2", "Option 3"])

# Main content
st.header("Welcome!")
st.write(f"You selected: {option}")

# Input
user_input = st.text_input("Enter something:")
if user_input:
    st.success(f"You entered: {user_input}")

# Button
if st.button("Click me!"):
    st.balloons()
    st.write("Button clicked!")
'''
        
        elif self.framework == "gradio":
            return '''import gradio as gr

def process(text):
    return f"You entered: {text}"

def greet(name):
    return f"Hello, {name}!"

with gr.Blocks(title="''' + self.name + '''") as demo:
    gr.Markdown("# 🚀 ''' + self.name + '''")
    gr.Markdown("Built with Gradio and Streamware")
    
    with gr.Tab("Text"):
        text_input = gr.Textbox(label="Input")
        text_output = gr.Textbox(label="Output")
        text_button = gr.Button("Process")
        text_button.click(process, inputs=text_input, outputs=text_output)
    
    with gr.Tab("Greeting"):
        name_input = gr.Textbox(label="Your name")
        greeting_output = gr.Textbox(label="Greeting")
        greet_button = gr.Button("Greet")
        greet_button.click(greet, inputs=name_input, outputs=greeting_output)

demo.launch(server_port=''' + str(self.port) + ''')
'''
        
        else:  # dash
            return '''import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

app = dash.Dash(__name__, title="''' + self.name + '''")

app.layout = html.Div([
    html.H1("🚀 ''' + self.name + '''"),
    html.P("Built with Dash and Streamware"),
    
    dcc.Input(id='input-text', type='text', placeholder='Enter something...'),
    html.Div(id='output-text'),
    
    dcc.Graph(id='example-graph')
])

@app.callback(
    Output('output-text', 'children'),
    Input('input-text', 'value')
)
def update_output(value):
    if value:
        return f'You entered: {value}'
    return 'Enter something above'

@app.callback(
    Output('example-graph', 'figure'),
    Input('input-text', 'value')
)
def update_graph(value):
    # Example graph
    fig = px.bar(x=['A', 'B', 'C'], y=[1, 3, 2])
    return fig

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=''' + str(self.port) + ''', debug=True)
'''
    
    def _generate_readme(self) -> str:
        """Generate README"""
        return f'''# {self.name}

Generated with Streamware WebApp component.

## Framework

{self.framework.title()}

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Run

```bash
# Using sq
sq webapp serve --framework {self.framework} --port {self.port}

# Or directly
python app.py
```

## Deploy

```bash
sq deploy k8s --apply --file deployment.yaml
```

## Built with Streamware

https://github.com/softreck/streamware
'''
    
    def _generate_dockerfile(self) -> str:
        """Generate Dockerfile"""
        return f'''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE {self.port}

CMD ["python", "app.py"]
'''


# Quick helpers
def create_webapp(framework: str, name: str, output: str = ".") -> Dict:
    """Quick web app creation"""
    from ..core import flow
    uri = f"webapp://create?framework={framework}&name={name}&output={output}"
    return flow(uri).run()
