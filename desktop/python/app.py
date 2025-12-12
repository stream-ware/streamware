#!/usr/bin/env python3
"""
Streamware Voice Shell - Desktop Application

A native desktop wrapper for the Voice Shell web UI using PyWebView.
Provides system tray integration, proper window management, and 
automatic backend server lifecycle management.
"""

import argparse
import asyncio
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# Add parent package to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class VoiceShellApp:
    """Desktop application for Voice Shell."""
    
    def __init__(
        self,
        port: int = 8765,
        http_port: int = 8766,
        model: str = "llama3.2",
        language: str = "en",
        verbose: bool = False,
    ):
        self.port = port
        self.http_port = http_port
        self.model = model
        self.language = language
        self.verbose = verbose
        
        self.server = None
        self.server_thread = None
        self.window = None
        self.tray = None
        
    def start_server(self):
        """Start the Voice Shell server in a background thread."""
        def run_server():
            try:
                from streamware.voice_shell_server import VoiceShellServer
                
                self.server = VoiceShellServer(
                    host="127.0.0.1",  # Localhost only for desktop
                    port=self.port,
                    model=self.model,
                    verbose=self.verbose,
                    default_language=self.language,
                )
                
                # Run the async server
                asyncio.run(self.server.run())
                
            except Exception as e:
                print(f"❌ Server error: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
    def stop_server(self):
        """Stop the server gracefully."""
        if self.server:
            self.server._running = False
            
    def create_tray_icon(self):
        """Create system tray icon."""
        try:
            import pystray
            from PIL import Image
            
            # Create a simple icon (blue circle)
            icon_size = 64
            image = Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
            
            # Draw a circle
            from PIL import ImageDraw
            draw = ImageDraw.Draw(image)
            draw.ellipse([4, 4, icon_size-4, icon_size-4], fill=(79, 195, 247, 255))
            draw.text((icon_size//4, icon_size//4), "🎤", fill=(255, 255, 255))
            
            def on_show(icon, item):
                if self.window:
                    self.window.show()
                    
            def on_hide(icon, item):
                if self.window:
                    self.window.hide()
                    
            def on_quit(icon, item):
                icon.stop()
                self.stop_server()
                if self.window:
                    self.window.destroy()
            
            menu = pystray.Menu(
                pystray.MenuItem("Show", on_show, default=True),
                pystray.MenuItem("Hide", on_hide),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", on_quit),
            )
            
            self.tray = pystray.Icon(
                "voice_shell",
                image,
                "Streamware Voice Shell",
                menu,
            )
            
            # Run tray in background
            tray_thread = threading.Thread(target=self.tray.run, daemon=True)
            tray_thread.start()
            
        except ImportError:
            print("⚠️ System tray not available (install pystray)")
        except Exception as e:
            print(f"⚠️ Tray icon error: {e}")
            
    def create_window(self):
        """Create the main application window."""
        import webview
        
        url = f"http://127.0.0.1:{self.http_port}"
        
        # Simple window - no JS API needed for this use case
        # The web UI handles everything via WebSocket
        self.window = webview.create_window(
            title="Streamware Voice Shell",
            url=url,
            width=1400,
            height=900,
            min_size=(800, 600),
            resizable=True,
        )
        
        return self.window
        
    def run(self):
        """Run the desktop application."""
        import webview
        
        print("🖥️ Starting Streamware Voice Shell Desktop...")
        print(f"   Port: {self.port}")
        print(f"   Language: {self.language}")
        
        # Start backend server
        print("🚀 Starting backend server...")
        self.start_server()
        
        # Create system tray
        self.create_tray_icon()
        
        # Create and run window (blocks until closed)
        print("🪟 Opening application window...")
        self.create_window()
        
        webview.start(debug=self.verbose)
        
        # Cleanup
        print("👋 Shutting down...")
        self.stop_server()


def main():
    parser = argparse.ArgumentParser(
        description="Streamware Voice Shell Desktop Application"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)"
    )
    parser.add_argument(
        "--lang", "-l",
        default="en",
        choices=["en", "pl", "de"],
        help="Interface language (default: en)"
    )
    parser.add_argument(
        "--model", "-m",
        default="llama3.2",
        help="LLM model (default: llama3.2)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    app = VoiceShellApp(
        port=args.port,
        http_port=args.port + 1,
        model=args.model,
        language=args.lang,
        verbose=args.verbose,
    )
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
