#!/usr/bin/env python3
"""
Voice Shell Server - WebSocket-based voice interaction with Streamware

Features:
- WebSocket real-time communication
- Browser-based STT (Web Speech API)
- Browser-based TTS or server-side TTS
- Event-driven architecture (simple event sourcing)
- Real-time shell output streaming

Usage:
    sq voice-shell          # Start server on port 8765
    sq voice-shell --port 9000
    
Then open http://localhost:8765 in browser
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import threading
import queue
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import uuid

try:
    import websockets
    from websockets.server import serve
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

from .config import config
from .llm_shell import LLMShell, ShellResult
from .i18n.translations import Translator, get_language


# =============================================================================

# Import from extracted modules
from .voice_shell_events import EventType, Event, EventStore, Session
from .voice_shell_input import VoiceInputProcessorMixin
from .voice_shell_html import get_voice_shell_html, get_voice_shell_html_from_template


class VoiceShellServer(VoiceInputProcessorMixin):
    """WebSocket server for voice-enabled shell interaction with multi-session support."""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        model: str = "llama3.2",
        verbose: bool = False,
        default_language: str = "en",
    ):
        self.host = host
        self.port = port
        self.model = model
        self.verbose = verbose
        
        # Event store
        self.events = EventStore()
        
        # Database for persistence
        from streamware.voice_shell.database import get_db
        self.db = get_db()
        
        # Load saved config first (needed for language)
        saved_config = self.db.get_all_config()
        
        # Language support with Translator (prefer saved, fallback to CLI arg)
        self.language = saved_config.get("language") or default_language
        if self.verbose:
            print(f"🔤 Server language: {self.language}")
        
        # Shell instance with language
        self.shell = LLMShell(model=model, language=self.language)
        if self.verbose:
            print(f"🔤 Shell language: {self.shell.language}")
        
        # Load saved config into shell context
        if saved_config.get("email"):
            self.shell.context["email"] = saved_config["email"]
        if saved_config.get("url"):
            self.shell.context["url"] = saved_config["url"]
        
        # Reusable translator (uses same language as shell)
        self.t = Translator(self.language)
        
        # Connected clients
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Multi-session support
        self.sessions: Dict[str, Session] = {}
        self.current_session_id: Optional[str] = None
        self._session_counter = 0
        
        # Restore sessions from database
        self._restore_sessions_from_db()
        
        # Current conversation state (for active input)
        self.pending_command: Optional[ShellResult] = None
        self.pending_options: Optional[List[tuple]] = None
        self.pending_input_type: Optional[str] = None
        self.pending_command_template: Optional[str] = None
        self.spelling_buffer: str = ""
        
        # HTTP server reference for cleanup
        self.http_server = None
        
        # Running process reference (for old single-process mode)
        self.running_process = None
        
        # Event loop reference for thread-safe broadcasting
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._pending_broadcasts: queue.Queue = queue.Queue()
    
    def _restore_sessions_from_db(self):
        """Restore previous sessions from database on startup."""
        try:
            recent_sessions = self.db.get_recent_sessions(limit=20)
            
            for session_record in recent_sessions:
                # Only restore completed/idle sessions (not running ones)
                if session_record.status in ('completed', 'idle', 'error'):
                    session = Session(
                        id=session_record.id,
                        name=session_record.name,
                        status=session_record.status,  # Keep original status
                    )
                    
                    # Load output history from database
                    logs = self.db.get_session_logs(session_record.id, limit=500)
                    session.output = [log['message'] for log in logs]
                    
                    self.sessions[session_record.id] = session
                    
                    # Track highest session number for counter
                    try:
                        num = int(session_record.id.replace('s', ''))
                        if num > self._session_counter:
                            self._session_counter = num
                    except ValueError:
                        pass
            
            if self.sessions:
                print(f"📂 Restored {len(self.sessions)} sessions from database")
                # Set current to most recent
                self.current_session_id = list(self.sessions.keys())[-1]
                
        except Exception as e:
            print(f"⚠️ Could not restore sessions: {e}")
    
    def _broadcast_from_thread(self, event: Event):
        """Thread-safe method to queue events for broadcast."""
        self._pending_broadcasts.put(event)
    
    async def _process_pending_broadcasts(self):
        """Process events queued from threads."""
        while True:
            try:
                # Non-blocking check for pending events
                while not self._pending_broadcasts.empty():
                    try:
                        event = self._pending_broadcasts.get_nowait()
                        await self.broadcast(event)
                    except queue.Empty:
                        break
                await asyncio.sleep(0.05)  # Check every 50ms
            except Exception as e:
                print(f"Broadcast error: {e}")
                await asyncio.sleep(0.1)
    
    def create_session(self, name: str = None) -> Session:
        """Create a new conversation session."""
        self._session_counter += 1
        session_id = f"s{self._session_counter}"
        if not name:
            name = f"Conversation {self._session_counter}"
        
        session = Session(id=session_id, name=name)
        self.sessions[session_id] = session
        self.current_session_id = session_id
        
        # Save to database
        self.db.create_session(session_id, name)
        
        # Reset conversation state
        self.pending_command = None
        self.pending_options = None
        self.pending_input_type = None
        self.spelling_buffer = ""
        
        return session
    
    def get_current_session(self) -> Optional[Session]:
        """Get the current active session."""
        if self.current_session_id and self.current_session_id in self.sessions:
            return self.sessions[self.current_session_id]
        return None
    
    def switch_session(self, session_id: str) -> Optional[Session]:
        """Switch to a different session."""
        if session_id in self.sessions:
            self.current_session_id = session_id
            # Reset pending state for new session
            self.pending_command = None
            self.pending_options = None
            
            session = self.sessions[session_id]
            
            # Load output from database if not in memory
            if not session.output:
                logs = self.db.get_session_logs(session_id, limit=500)
                session.output = [log['message'] for log in logs]
            
            return session
        return None
    
    def close_session(self, session_id: str):
        """Close and cleanup a session."""
        print(f"🗑️ Closing session: {session_id}")
        
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.stop()
            del self.sessions[session_id]
            print(f"   ✅ Removed from memory")
            
            # Delete from database
            try:
                self.db.delete_session(session_id)
                print(f"   ✅ Deleted from database")
            except Exception as e:
                print(f"   ⚠️ Could not delete session from DB: {e}")
            
            # If closing current session, switch to another
            if self.current_session_id == session_id:
                if self.sessions:
                    self.current_session_id = list(self.sessions.keys())[-1]
                else:
                    self.current_session_id = None
        else:
            print(f"   ⚠️ Session not found in memory: {session_id}")
        
    async def broadcast(self, event: Event):
        """Broadcast event to all connected clients."""
        self.events.append(event)
        
        if self.clients:
            message = event.to_json()
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
    
    async def handle_client(self, websocket):
        """Handle a client connection."""
        self.clients.add(websocket)
        client_id = str(uuid.uuid4())[:8]
        
        # Send connected event
        await self.broadcast(Event(
            type=EventType.CLIENT_CONNECTED,
            data={"client_id": client_id}
        ))
        
        # Send current config from SQLite (CQRS - event sourcing state)
        await self._send_config(websocket)
        
        # Send current context
        await websocket.send(Event(
            type=EventType.CONTEXT_UPDATED,
            data=self.shell.context
        ).to_json())
        
        # Send recent events (event sourcing - replay)
        for event in self.events.get_recent(20):
            await websocket.send(event.to_json())
        
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            await self.broadcast(Event(
                type=EventType.CLIENT_DISCONNECTED,
                data={"client_id": client_id}
            ))
    
    def _get_sessions_list(self) -> List[Dict]:
        """Get list of all sessions."""
        sessions_list = [s.to_dict() for s in self.sessions.values()]
        if self.verbose:
            print(f"📋 Sessions: {len(sessions_list)} - {[s['id']+':'+s['status'] for s in sessions_list]}")
        return sessions_list
    
    async def speak(self, text: str):
        """Send TTS message and save to session history AND database."""
        # Save to current session output AND database
        session = self.get_current_session()
        if session:
            line = f"🔊 {text}"
            session.output.append(line)
            self.db.log_output(session.id, line, "tts")
        
        # Broadcast TTS event
        await self.broadcast(Event(
            type=EventType.TTS_SPEAK,
            data={"text": text}
        ))
    
    async def _send_config(self, websocket=None):
        """Send current config to client (CQRS query response)."""
        config = self.db.get_all_config()
        event = Event(
            type=EventType.CONFIG_LOADED,
            data={
                "language": config.get("language", "en"),
                "email": config.get("email", ""),
                "url": config.get("url", ""),
            }
        )
        if websocket:
            await websocket.send(json.dumps({"type": event.type.value, "data": event.data}))
        else:
            await self.broadcast(event)
    
    async def execute_command(self, result: ShellResult):
        """Execute the command in a separate thread for the current session."""
        # Ensure we have a session
        session = self.get_current_session()
        if not session:
            session = self.create_session()
        
        # Check and inject missing params
        missing, cmd = self.shell._check_missing_params(result.shell_command)
        
        if missing:
            await self.broadcast(Event(
                type=EventType.COMMAND_ERROR,
                data={"error": f"Missing parameters: {', '.join(missing)}"}
            ))
            return
        
        # Inject language parameter for TTS commands if not English
        if self.language != 'en' and '--tts' in cmd and '--lang' not in cmd:
            cmd = cmd + f" --lang {self.language}"
        
        # Get full path to sq
        import shutil
        sq_path = shutil.which("sq")
        if not sq_path:
            python_path = sys.executable
            sq_path = os.path.join(os.path.dirname(python_path), "sq")
        
        if sq_path and os.path.exists(sq_path):
            cmd = cmd.replace("sq ", f"{sq_path} ", 1)
        
        # Update session
        session.command = cmd
        session.status = "running"
        session.name = result.explanation[:30] if result.explanation else cmd[:30]
        
        # Log command to database
        self.db.log_command(
            session_id=session.id,
            user_input=result.explanation or "",
            parsed_command=cmd,
            explanation=result.explanation,
            executed=True
        )
        
        # Debug: Show full command being executed
        if self.verbose:
            print(f"🚀 Executing: {cmd}")
        
        await self.broadcast(Event(
            type=EventType.COMMAND_EXECUTED,
            data={"command": cmd, "session_id": session.id}
        ))
        
        await self.speak(self.t.conv("executing"))
        
        # Update sessions list
        await self.broadcast(Event(
            type=EventType.SESSION_CREATED,
            data={"session": session.to_dict(), "sessions": self._get_sessions_list()}
        ))
        
        # Run command in background thread
        def run_in_thread():
            self._run_command_sync(session, cmd)
        
        session.thread = threading.Thread(target=run_in_thread, daemon=True)
        session.thread.start()
        
        # Update session list to show running status
        await self.broadcast(Event(
            type=EventType.SESSION_CREATED,
            data={"session": session.to_dict(), "sessions": self._get_sessions_list()}
        ))
    
    def _run_command_sync(self, session: Session, cmd: str):
        """Run command synchronously in a thread."""
        try:
            session.process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            
            # Stream output
            for line in iter(session.process.stdout.readline, ''):
                if not line:
                    break
                line = line.rstrip()
                session.output.append(line)
                
                # Log ALL output to database for history persistence
                self.db.log_output(session.id, line, "output")
                
                # Broadcast to clients via queue (thread-safe)
                self._broadcast_from_thread(Event(
                    type=EventType.SESSION_OUTPUT,
                    data={"session_id": session.id, "line": line}
                ))
            
            # Process completed
            return_code = session.process.wait()
            session.status = "completed" if return_code == 0 else "error"
            
            # End session in database
            self.db.end_session(session.id, session.status)
            session.process = None
            
            self._broadcast_from_thread(Event(
                type=EventType.COMMAND_COMPLETED,
                data={"session_id": session.id, "return_code": return_code}
            ))
            
            # Update sessions list
            self._broadcast_from_thread(Event(
                type=EventType.SESSION_CREATED,
                data={"session": session.to_dict(), "sessions": self._get_sessions_list()}
            ))
            
        except Exception as e:
            session.status = "error"
            session.output.append(f"Error: {e}")
            self._broadcast_from_thread(Event(
                type=EventType.COMMAND_ERROR,
                data={"session_id": session.id, "error": str(e)}
            ))
    
    async def stop_current_session(self):
        """Stop the current session's process."""
        session = self.get_current_session()
        if session and session.process:
            session.stop()
            await self.broadcast(Event(
                type=EventType.COMMAND_COMPLETED,
                data={"session_id": session.id, "stopped": True}
            ))
            await self.broadcast(Event(
                type=EventType.TTS_SPEAK,
                data={"text": "Process stopped."}
            ))
    
    async def stop_session_by_id(self, session_id: str):
        """Stop a specific session's process by ID."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if session.process:
                session.stop()
                await self.broadcast(Event(
                    type=EventType.COMMAND_COMPLETED,
                    data={"session_id": session.id, "stopped": True}
                ))
                # Update sessions list
                await self.broadcast(Event(
                    type=EventType.SESSION_CREATED,
                    data={"session": session.to_dict(), "sessions": self._get_sessions_list()}
                ))
                print(f"⏹ Process stopped: {session.name}", flush=True)
    
    async def execute_command_old(self, result: ShellResult):
        """Execute the command (old single-process method)."""
        # Check and inject missing params
        missing, cmd = self.shell._check_missing_params(result.shell_command)
        
        if missing:
            await self.broadcast(Event(
                type=EventType.COMMAND_ERROR,
                data={"error": f"Missing parameters: {', '.join(missing)}"}
            ))
            return
        
        # Get full path to sq
        import shutil
        sq_path = shutil.which("sq")
        if not sq_path:
            python_path = sys.executable
            sq_path = os.path.join(os.path.dirname(python_path), "sq")
        
        if sq_path and os.path.exists(sq_path):
            cmd = cmd.replace("sq ", f"{sq_path} ", 1)
        
        await self.broadcast(Event(
            type=EventType.COMMAND_EXECUTED,
            data={"command": cmd}
        ))
        
        await self.broadcast(Event(
            type=EventType.TTS_SPEAK,
            data={"text": "Executing command."}
        ))
        
        # Run command in background
        running_process = None
        try:
            running_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            
            # Stream output
            asyncio.create_task(self.stream_output())
            
        except Exception as e:
            await self.broadcast(Event(
                type=EventType.COMMAND_ERROR,
                data={"error": str(e)}
            ))
    
    async def stream_output(self):
        """Stream command output to clients."""
        if not self.running_process:
            return
        
        try:
            for line in iter(self.running_process.stdout.readline, ''):
                if not line:
                    break
                
                await self.broadcast(Event(
                    type=EventType.COMMAND_OUTPUT,
                    data={"line": line.rstrip()}
                ))
                
                # Small delay to prevent flooding
                await asyncio.sleep(0.05)
            
            # Process completed
            return_code = self.running_process.wait()
            await self.broadcast(Event(
                type=EventType.COMMAND_COMPLETED,
                data={"return_code": return_code}
            ))
            
        except Exception as e:
            await self.broadcast(Event(
                type=EventType.COMMAND_ERROR,
                data={"error": str(e)}
            ))
        finally:
            self.running_process = None
    
    async def stop_process(self):
        """Stop the running process."""
        if self.running_process:
            self.running_process.terminate()
            self.running_process = None
            
            await self.broadcast(Event(
                type=EventType.COMMAND_COMPLETED,
                data={"stopped": True}
            ))
            
            await self.broadcast(Event(
                type=EventType.TTS_SPEAK,
                data={"text": "Process stopped."}
            ))
        
        # Also stop any sq watch processes
        os.system("pkill -f 'sq watch' 2>/dev/null")
    
    def warmup_llm(self):
        """Warmup LLM model to avoid cold start delays."""
        import requests
        
        # Get vision model from config
        vision_model = config.get("SQ_MODEL", "llava:7b")
        ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        
        print(f"🔥 Warming up LLM model: {vision_model}...")
        
        try:
            # Simple warmup request
            resp = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": vision_model, "prompt": "Hello", "stream": False},
                timeout=30
            )
            if resp.ok:
                print(f"   ✅ Model {vision_model} ready!")
                return True
            else:
                print(f"   ⚠️  Model warmup returned: {resp.status_code}")
        except requests.exceptions.Timeout:
            print(f"   ⚠️  Model warmup timeout (model may still be loading)")
        except Exception as e:
            print(f"   ⚠️  Model warmup failed: {e}")
        
        return False
    
    async def run(self):
        """Run the WebSocket server."""
        if not HAS_WEBSOCKETS:
            print("❌ websockets package required. Install with: pip install websockets")
            return
        
        http_port = self.port + 1
        
        print(f"🎤 Voice Shell Server starting...")
        print(f"   WebSocket: ws://localhost:{self.port}")
        print(f"   Model: {self.model}")
        print()
        
        # Warmup LLM model in background
        import threading
        warmup_thread = threading.Thread(target=self.warmup_llm, daemon=True)
        warmup_thread.start()
        
        # Start HTTP server for static files
        http_task = asyncio.create_task(self.serve_http())
        
        # Start broadcast processor for thread-safe events
        broadcast_task = asyncio.create_task(self._process_pending_broadcasts())
        
        # Start WebSocket server
        try:
            async with serve(self.handle_client, self.host, self.port):
                print(f"✅ Server running!")
                print(f"   👉 Open http://localhost:{http_port} in browser")
                print("   Press Ctrl+C to stop")
                await asyncio.Future()  # Run forever
        finally:
            # Cleanup on exit
            broadcast_task.cancel()
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources on exit."""
        print("\n🧹 Cleaning up...")
        
        # Stop running process
        if self.running_process:
            self.running_process.terminate()
            self.running_process = None
        
        # Stop HTTP server
        if self.http_server:
            self.http_server.shutdown()
            self.http_server = None
        
        # Kill any sq processes
        os.system("pkill -f 'sq watch' 2>/dev/null")
        os.system("pkill -f 'sq live' 2>/dev/null")
        
        print("✅ Cleanup complete")
    
    async def serve_http(self):
        """Serve the web UI with authentication."""
        from http.server import HTTPServer, SimpleHTTPRequestHandler
        from urllib.parse import urlparse, parse_qs
        import threading
        import http.cookies
        
        voice_shell_server = self  # Reference for handler
        
        # Create handler that serves our HTML with auth
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)
            
            def _get_session_user(self):
                """Get user from session cookie."""
                try:
                    from .voice_shell.auth import get_auth_db
                    
                    cookie_header = self.headers.get('Cookie', '')
                    cookies = http.cookies.SimpleCookie(cookie_header)
                    
                    if 'session' in cookies:
                        session_token = cookies['session'].value
                        db = get_auth_db()
                        return db.verify_session(session_token)
                except Exception:
                    pass
                return None
            
            def _send_json(self, data: dict, status: int = 200):
                """Send JSON response."""
                self.send_response(status)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            
            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path
                query = parse_qs(parsed.query)
                
                # Main page
                if path == "/" or path == "/index.html":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    html = get_voice_shell_html_from_template(self.server.ws_port, self.server.language)
                    self.wfile.write(html.encode())
                
                # Static files (CSS, JS)
                elif path.startswith("/static/"):
                    filename = path.replace("/static/", "")
                    templates_dir = Path(__file__).parent / "templates"
                    file_path = templates_dir / filename
                    
                    if file_path.exists() and file_path.is_file():
                        # Determine content type
                        content_type = "text/plain"
                        if filename.endswith(".css"):
                            content_type = "text/css"
                        elif filename.endswith(".js"):
                            content_type = "application/javascript"
                        elif filename.endswith(".html"):
                            content_type = "text/html"
                        
                        self.send_response(200)
                        self.send_header("Content-type", content_type)
                        self.end_headers()
                        self.wfile.write(file_path.read_bytes())
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                # Auth: Verify magic link
                elif path == "/auth/verify":
                    token = query.get('token', [None])[0]
                    if not token:
                        self._send_json({"error": "Missing token"}, 400)
                        return
                    
                    try:
                        from .voice_shell.auth import verify_magic_link_token
                        user, session_token = verify_magic_link_token(token)
                        
                        if user and session_token:
                            # Set session cookie and redirect to main page
                            self.send_response(302)
                            cookie = f"session={session_token}; Path=/; Max-Age={30*24*60*60}; HttpOnly; SameSite=Lax"
                            self.send_header("Set-Cookie", cookie)
                            self.send_header("Location", "/")
                            self.end_headers()
                            print(f"✅ User logged in: {user.email}")
                        else:
                            self.send_response(200)
                            self.send_header("Content-type", "text/html")
                            self.end_headers()
                            self.wfile.write(b"<h1>Invalid or expired link</h1><p><a href='/'>Go back</a></p>")
                    except Exception as e:
                        self._send_json({"error": str(e)}, 500)
                
                # Auth: Get current user
                elif path == "/auth/me":
                    user = self._get_session_user()
                    if user:
                        self._send_json({
                            "authenticated": True,
                            "user": {"id": user.id, "email": user.email}
                        })
                    else:
                        self._send_json({"authenticated": False})
                
                # Auth: Logout
                elif path == "/auth/logout":
                    try:
                        from .voice_shell.auth import get_auth_db
                        
                        cookie_header = self.headers.get('Cookie', '')
                        cookies = http.cookies.SimpleCookie(cookie_header)
                        
                        if 'session' in cookies:
                            db = get_auth_db()
                            db.delete_session(cookies['session'].value)
                        
                        self.send_response(302)
                        self.send_header("Set-Cookie", "session=; Path=/; Max-Age=0")
                        self.send_header("Location", "/")
                        self.end_headers()
                    except Exception as e:
                        self._send_json({"error": str(e)}, 500)
                
                # Auth: Get user settings (grid positions)
                elif path == "/auth/settings":
                    user = self._get_session_user()
                    if not user:
                        self._send_json({"error": "Not authenticated"}, 401)
                        return
                    
                    try:
                        from .voice_shell.auth import get_auth_db
                        db = get_auth_db()
                        settings = db.get_user_settings(user.id)
                        self._send_json(settings)
                    except Exception as e:
                        self._send_json({"error": str(e)}, 500)
                
                else:
                    super().do_GET()
            
            def do_POST(self):
                parsed = urlparse(self.path)
                path = parsed.path
                
                # Auth: Request magic link
                if path == "/auth/login":
                    try:
                        content_length = int(self.headers.get('Content-Length', 0))
                        body = self.rfile.read(content_length).decode()
                        data = json.loads(body) if body else {}
                        
                        email = data.get('email', '').strip()
                        if not email or '@' not in email:
                            self._send_json({"error": "Invalid email"}, 400)
                            return
                        
                        from .voice_shell.auth import send_magic_link_email
                        
                        # Get base URL from request
                        host = self.headers.get('Host', f'localhost:{self.server.server_port}')
                        base_url = f"http://{host}"
                        
                        success = send_magic_link_email(email, base_url)
                        
                        if success:
                            self._send_json({"success": True, "message": "Magic link sent! Check your email."})
                        else:
                            self._send_json({"error": "Failed to send email"}, 500)
                    except Exception as e:
                        self._send_json({"error": str(e)}, 500)
                
                # Auth: Save user settings (grid positions)
                elif path == "/auth/settings":
                    user = self._get_session_user()
                    if not user:
                        self._send_json({"error": "Not authenticated"}, 401)
                        return
                    
                    try:
                        from .voice_shell.auth import get_auth_db
                        
                        content_length = int(self.headers.get('Content-Length', 0))
                        body = self.rfile.read(content_length).decode()
                        settings = json.loads(body) if body else {}
                        
                        db = get_auth_db()
                        db.save_user_settings(user.id, settings)
                        
                        self._send_json({"success": True})
                    except Exception as e:
                        self._send_json({"error": str(e)}, 500)
                
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Suppress logging
        
        # Run HTTP server on port+1
        http_port = self.port + 1
        server = HTTPServer(("0.0.0.0", http_port), Handler)
        server.ws_port = self.port  # Store WS port for HTML to connect to
        server.language = self.language  # Use server's language
        self.http_server = server  # Store reference for cleanup
        
        print(f"   HTTP UI: http://localhost:{http_port}")
        print(f"   Auth: POST /auth/login with {{email}} for magic link")
        
        # Run in thread
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    """Run the voice shell server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Streamware Voice Shell Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", "-p", type=int, default=8765, help="WebSocket port (default: 8765)")
    parser.add_argument("--model", "-m", default="llama3.2", help="LLM model (default: llama3.2)")
    
    args = parser.parse_args()
    
    server = VoiceShellServer(
        host=args.host,
        port=args.port,
        model=args.model,
    )
    
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")


if __name__ == "__main__":
    main()
