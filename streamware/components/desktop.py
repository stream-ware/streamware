"""
Desktop App Component for Streamware

Create desktop applications with popular frameworks.
Supports PyQt, Tkinter, Kivy, and Electron.

# Menu:
- [Quick Start](#quick-start)
- [Frameworks](#frameworks)
- [Examples](#examples)
"""

from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Any, Dict
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


@register("desktop")
@register("gui")
class DesktopAppComponent(Component):
    """
    Desktop application generator
    
    Frameworks:
    - tkinter: Simple Tkinter GUI (built-in)
    - pyqt: PyQt5/PyQt6 professional GUI
    - kivy: Cross-platform Kivy
    - electron: Electron with Python backend
    
    Operations:
    - create: Create new desktop app
    - run: Run the application
    - build: Build executable
    
    URI Examples:
        desktop://create?framework=tkinter&name=myapp
        desktop://create?framework=pyqt&name=calculator
        desktop://run?framework=tkinter
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    FRAMEWORKS = {
        "tkinter": {
            "packages": [],  # Built-in
            "installer": None
        },
        "pyqt": {
            "packages": ["PyQt6"],
            "installer": "PyQt6"
        },
        "kivy": {
            "packages": ["kivy[base]"],
            "installer": "kivy[base]"
        },
        "electron": {
            "packages": ["flask"],
            "installer": "flask"
        }
    }
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "create"
        
        self.framework = uri.get_param("framework", "tkinter")
        self.name = uri.get_param("name", "myapp")
        self.auto_install = uri.get_param("auto_install", True)
        self.output_dir = uri.get_param("output", ".")
    
    def process(self, data: Any) -> Dict:
        """Process desktop app operation"""
        if self.auto_install:
            self._ensure_dependencies()
        
        operations = {
            "create": self._create,
            "run": self._run,
            "build": self._build,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _ensure_dependencies(self):
        """Ensure framework dependencies are installed"""
        if self.framework not in self.FRAMEWORKS:
            raise ComponentError(f"Unknown framework: {self.framework}")
        
        installer = self.FRAMEWORKS[self.framework]["installer"]
        if installer:
            try:
                __import__(installer.split("[")[0].replace("-", "_"))
            except ImportError:
                logger.info(f"Installing {installer}...")
                subprocess.run(
                    ["pip", "install", installer],
                    check=True,
                    capture_output=True
                )
    
    def _create(self, data: Any) -> Dict:
        """Create new desktop app"""
        output_path = Path(self.output_dir) / self.name
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate app code
        app_content = self._generate_app_code()
        
        with open(output_path / "app.py", 'w') as f:
            f.write(app_content)
        
        # Generate requirements
        if self.FRAMEWORKS[self.framework]["packages"]:
            with open(output_path / "requirements.txt", 'w') as f:
                f.write("\n".join(self.FRAMEWORKS[self.framework]["packages"]))
        
        # Generate README
        readme = f"""# {self.name}

Desktop application built with {self.framework.title()} and Streamware.

## Run

```bash
python app.py
```

## Build Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed app.py
```
"""
        with open(output_path / "README.md", 'w') as f:
            f.write(readme)
        
        return {
            "success": True,
            "framework": self.framework,
            "name": self.name,
            "path": str(output_path)
        }
    
    def _run(self, data: Any) -> Dict:
        """Run the application"""
        subprocess.run(["python", "app.py"])
        return {"success": True}
    
    def _build(self, data: Any) -> Dict:
        """Build executable"""
        # Install PyInstaller if needed
        try:
            __import__("PyInstaller")
        except ImportError:
            subprocess.run(["pip", "install", "pyinstaller"], check=True)
        
        # Build
        subprocess.run([
            "pyinstaller",
            "--onefile",
            "--windowed",
            "--name", self.name,
            "app.py"
        ])
        
        return {"success": True, "executable": f"dist/{self.name}"}
    
    def _generate_app_code(self) -> str:
        """Generate app code based on framework"""
        if self.framework == "tkinter":
            return '''import tkinter as tk
from tkinter import ttk, messagebox

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("''' + self.name + '''")
        self.geometry("600x400")
        
        # Create UI
        self.create_widgets()
    
    def create_widgets(self):
        # Title
        title = ttk.Label(self, text="''' + self.name + '''", font=("Arial", 20))
        title.pack(pady=20)
        
        # Input frame
        input_frame = ttk.Frame(self)
        input_frame.pack(pady=10)
        
        ttk.Label(input_frame, text="Enter text:").grid(row=0, column=0, padx=5)
        self.entry = ttk.Entry(input_frame, width=30)
        self.entry.grid(row=0, column=1, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Submit", command=self.on_submit).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear", command=self.on_clear).pack(side=tk.LEFT, padx=5)
        
        # Output
        self.output = tk.Text(self, height=10, width=60)
        self.output.pack(pady=10)
    
    def on_submit(self):
        text = self.entry.get()
        if text:
            self.output.insert(tk.END, f"You entered: {text}\\n")
            messagebox.showinfo("Success", "Text submitted!")
        else:
            messagebox.showwarning("Warning", "Please enter some text")
    
    def on_clear(self):
        self.entry.delete(0, tk.END)
        self.output.delete(1.0, tk.END)

if __name__ == "__main__":
    app = App()
    app.mainloop()
'''
        
        elif self.framework == "pyqt":
            return '''import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QMessageBox)
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("''' + self.name + '''")
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Title
        title = QLabel("''' + self.name + '''")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Input section
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Enter text:"))
        self.input_field = QLineEdit()
        input_layout.addWidget(self.input_field)
        layout.addLayout(input_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        submit_btn = QPushButton("Submit")
        submit_btn.clicked.connect(self.on_submit)
        button_layout.addWidget(submit_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.on_clear)
        button_layout.addWidget(clear_btn)
        layout.addLayout(button_layout)
        
        # Output
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)
    
    def on_submit(self):
        text = self.input_field.text()
        if text:
            self.output.append(f"You entered: {text}")
            QMessageBox.information(self, "Success", "Text submitted!")
        else:
            QMessageBox.warning(self, "Warning", "Please enter some text")
    
    def on_clear(self):
        self.input_field.clear()
        self.output.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
'''
        
        else:  # kivy
            return '''from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button

class MainLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10
        
        # Title
        self.add_widget(Label(text='''' + self.name + '''', font_size=30))
        
        # Input
        input_layout = BoxLayout(size_hint_y=0.1)
        input_layout.add_widget(Label(text='Enter text:', size_hint_x=0.3))
        self.text_input = TextInput(multiline=False)
        input_layout.add_widget(self.text_input)
        self.add_widget(input_layout)
        
        # Buttons
        button_layout = BoxLayout(size_hint_y=0.1)
        submit_btn = Button(text='Submit')
        submit_btn.bind(on_press=self.on_submit)
        button_layout.add_widget(submit_btn)
        
        clear_btn = Button(text='Clear')
        clear_btn.bind(on_press=self.on_clear)
        button_layout.add_widget(clear_btn)
        self.add_widget(button_layout)
        
        # Output
        self.output = TextInput(readonly=True)
        self.add_widget(self.output)
    
    def on_submit(self, instance):
        text = self.text_input.text
        if text:
            self.output.text += f"You entered: {text}\\n"
    
    def on_clear(self, instance):
        self.text_input.text = ''
        self.output.text = ''

class ''' + self.name.title() + '''App(App):
    def build(self):
        return MainLayout()

if __name__ == '__main__':
    ''' + self.name.title() + '''App().run()
'''


# Quick helper
def create_desktop_app(framework: str, name: str) -> Dict:
    """Quick desktop app creation"""
    from ..core import flow
    uri = f"desktop://create?framework={framework}&name={name}"
    return flow(uri).run()
