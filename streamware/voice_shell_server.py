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
# EVENT SOURCING
# =============================================================================

class EventType(str, Enum):
    """Event types for the voice shell."""
    # User events
    VOICE_INPUT = "voice_input"
    TEXT_INPUT = "text_input"
    COMMAND_CONFIRM = "command_confirm"
    
    # Session events
    SESSION_CREATED = "session_created"
    SESSION_SWITCHED = "session_switched"
    SESSION_CLOSED = "session_closed"
    SESSION_OUTPUT = "session_output"
    COMMAND_CANCEL = "command_cancel"
    
    # System events
    COMMAND_PARSED = "command_parsed"
    COMMAND_EXECUTED = "command_executed"
    COMMAND_OUTPUT = "command_output"
    COMMAND_ERROR = "command_error"
    COMMAND_COMPLETED = "command_completed"
    
    # TTS events
    TTS_SPEAK = "tts_speak"
    TTS_COMPLETE = "tts_complete"
    
    # Context events
    CONTEXT_UPDATED = "context_updated"
    LANGUAGE_CHANGED = "language_changed"
    CONFIG_LOADED = "config_loaded"
    VARIABLE_CHANGED = "variable_changed"
    
    # Connection events
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"


@dataclass
class Event:
    """Event for event sourcing."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: EventType = EventType.TEXT_INPUT
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "data": self.data,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class EventStore:
    """Simple in-memory event store."""
    
    def __init__(self, max_events: int = 1000):
        self.events: List[Event] = []
        self.max_events = max_events
        self.subscribers: List[callable] = []
    
    def append(self, event: Event):
        """Append event and notify subscribers."""
        self.events.append(event)
        
        # Trim old events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Notify subscribers
        for subscriber in self.subscribers:
            try:
                subscriber(event)
            except Exception as e:
                print(f"Event subscriber error: {e}")
    
    def subscribe(self, callback: callable):
        """Subscribe to events."""
        self.subscribers.append(callback)
    
    def get_recent(self, count: int = 50) -> List[Event]:
        """Get recent events."""
        return self.events[-count:]


# =============================================================================
# VOICE SHELL SERVER
# =============================================================================

@dataclass
class Session:
    """A single conversation session with its own process."""
    id: str
    name: str
    command: str = ""
    status: str = "idle"  # idle, pending, running, completed, error
    process: Optional[subprocess.Popen] = None
    output: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    thread: Optional[threading.Thread] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "status": self.status,
            "output_lines": len(self.output),
            "created_at": self.created_at.isoformat(),
            "has_process": self.process is not None or self.status in ('running', 'completed', 'error'),
        }
    
    def stop(self):
        """Stop the running process."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            self.process = None
        self.status = "stopped"


class VoiceShellServer:
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
    
    async def handle_message(self, websocket, message: str):
        """Handle incoming message from client."""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "text_input")
            content = data.get("content", "")
            
            # Session management commands
            if msg_type == "new_session":
                session = self.create_session(content or None)
                await self.broadcast(Event(
                    type=EventType.SESSION_CREATED,
                    data={"session": session.to_dict(), "sessions": self._get_sessions_list()}
                ))
                await self.speak(self.t.status("new_conversation"))
                return
            
            elif msg_type == "switch_session":
                session = self.switch_session(content)
                if session:
                    await self.broadcast(Event(
                        type=EventType.SESSION_SWITCHED,
                        data={
                            "session": session.to_dict(), 
                            "output": session.output[-100:],  # Last 100 lines
                            "sessions": self._get_sessions_list()
                        }
                    ))
                else:
                    # Session not found - send error
                    await self.broadcast(Event(
                        type=EventType.SESSION_OUTPUT,
                        data={"session_id": self.current_session_id, "line": f"⚠️ Session {content} not found. Available: {list(self.sessions.keys())}"}
                    ))
                return
            
            elif msg_type == "close_session":
                self.close_session(content)
                await self.broadcast(Event(
                    type=EventType.SESSION_CLOSED,
                    data={"session_id": content, "sessions": self._get_sessions_list()}
                ))
                return
            
            elif msg_type == "get_sessions":
                # Create first session if none exist
                if not self.sessions:
                    session = self.create_session()
                    await self.broadcast(Event(
                        type=EventType.SESSION_CREATED,
                        data={"session": session.to_dict(), "sessions": self._get_sessions_list()}
                    ))
                    await self.speak(self.t.status("new_conversation"))
                else:
                    # Send existing sessions with current session output
                    current_session = self.get_current_session()
                    await websocket.send(json.dumps({
                        "type": "sessions_list",
                        "data": {
                            "sessions": self._get_sessions_list(), 
                            "current": self.current_session_id,
                            "output": current_session.output[-100:] if current_session else []
                        }
                    }))
                return
            
            elif msg_type == "voice_input":
                # Voice input from browser STT
                # Store to session output for history AND database
                session = self.get_current_session()
                if session:
                    line = f"> {content}"
                    session.output.append(line)
                    self.db.log_output(session.id, line, "input")
                
                await self.broadcast(Event(
                    type=EventType.VOICE_INPUT,
                    data={"text": content, "source": "browser_stt"}
                ))
                await self.process_input(content)
                
            elif msg_type == "text_input":
                # Text input
                # Store to session output for history AND database
                session = self.get_current_session()
                if session:
                    line = f"> {content}"
                    session.output.append(line)
                    self.db.log_output(session.id, line, "input")
                
                await self.broadcast(Event(
                    type=EventType.TEXT_INPUT,
                    data={"text": content}
                ))
                await self.process_input(content)
                
            elif msg_type == "confirm":
                # Confirm pending command
                if self.pending_command:
                    await self.execute_command(self.pending_command)
                    self.pending_command = None
                    
            elif msg_type == "cancel":
                # Cancel pending command
                if self.pending_command:
                    await self.broadcast(Event(
                        type=EventType.COMMAND_CANCEL,
                        data={"command": self.pending_command.shell_command}
                    ))
                    self.pending_command = None
                    
            elif msg_type == "stop":
                # Stop current session's process
                await self.stop_current_session()
            
            elif msg_type == "stop_session":
                # Stop specific session's process by ID
                await self.stop_session_by_id(content)
            
            elif msg_type == "set_language":
                # Set conversation language (CQRS command - persists to SQLite)
                self.language = content
                self.shell.language = content
                self.shell.t.set_language(content)  # Update shell translator
                self.t.set_language(content)  # Update server translator
                self.db.set_config("language", content)
                
                # Record event (event sourcing)
                self.events.append(Event(
                    type=EventType.LANGUAGE_CHANGED,
                    data={"language": content}
                ))
                
                # Broadcast to all clients
                await self.broadcast(Event(
                    type=EventType.LANGUAGE_CHANGED,
                    data={"language": content}
                ))
                print(f"🌐 Language set to: {content}", flush=True)
            
            elif msg_type == "get_config":
                # CQRS query - return current config from SQLite
                await self._send_config(websocket)
            
            elif msg_type == "set_variable":
                # CQRS command - set variable in context and SQLite
                key = content.get("key")
                value = content.get("value")
                if key:
                    # Update shell context
                    self.shell.context[key] = value
                    # Persist to SQLite
                    self.db.set_config(key, value)
                    
                    # Record event (event sourcing)
                    self.events.append(Event(
                        type=EventType.VARIABLE_CHANGED,
                        data={"key": key, "value": value}
                    ))
                    
                    # Broadcast to all clients
                    await self.broadcast(Event(
                        type=EventType.VARIABLE_CHANGED,
                        data={"key": key, "value": value}
                    ))
                    print(f"📝 Variable set: {key}={value[:50] if value else '(empty)'}...", flush=True)
            
            elif msg_type == "remove_variable":
                # CQRS command - remove variable
                key = content.get("key")
                if key and key in self.shell.context:
                    del self.shell.context[key]
                    self.db.set_config(key, "")  # Clear in SQLite
                    
                    # Broadcast removal
                    await self.broadcast(Event(
                        type=EventType.VARIABLE_CHANGED,
                        data={"key": key, "value": None, "removed": True}
                    ))
                    print(f"🗑️ Variable removed: {key}", flush=True)
                
        except json.JSONDecodeError:
            # Plain text input
            await self.process_input(message)
    
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
    
    async def process_input(self, text: str):
        """Process user input through LLM shell."""
        if not text.strip():
            return
        
        lower = text.lower().strip()
        
        # Multi-language cancel keywords - can cancel at ANY stage
        cancel_words = (
            # English
            "cancel", "stop", "nevermind", "never mind", "abort", "quit", "reset",
            # Polish
            "anuluj", "przerwij", "stop", "koniec", "zrezygnuj", "cofnij",
            # German
            "abbrechen", "stopp", "beenden", "zurück",
            # Spanish
            "cancelar", "parar", "detener",
            # French
            "annuler", "arrêter", "arreter",
        )
        
        # Multi-language confirmation keywords
        confirm_words = (
            # English
            "yes", "yeah", "okay", "ok", "execute", "do it", "run", "confirm", "sure",
            # Polish
            "tak", "dobrze", "wykonaj", "potwierdź", "potwierdzam", "zgoda",
            # German
            "ja", "jawohl", "ausführen", "bestätigen",
            # Spanish
            "sí", "si", "vale", "ejecutar",
            # French
            "oui", "d'accord", "exécuter",
        )
        
        # Multi-language rejection keywords
        reject_words = (
            # English
            "no", "nope", "don't", "dont",
            # Polish
            "nie", "niedobrze",
            # German
            "nein",
            # Spanish/French
            "non",
        )
        
        # Check for cancel at ANY stage - this takes priority
        if any(w == lower or lower.startswith(w + " ") for w in cancel_words):
            # Clear all pending states
            had_pending = self.pending_command or self.pending_options or self.pending_input_type
            self.pending_command = None
            self.pending_options = None
            self.pending_input_type = None
            self.pending_command_template = None
            self.spelling_buffer = ""
            
            if had_pending:
                await self.speak(self.t.conv("goal_cancelled"))
            else:
                await self.speak(self.t.conv("how_can_help"))
            return
        
        # Handle yes/no for pending command confirmation
        if self.pending_command and lower in confirm_words:
            await self.execute_command(self.pending_command)
            self.pending_command = None
            return
        
        if self.pending_command and lower in reject_words:
            self.pending_command = None
            await self.speak(self.t.conv("goal_cancelled"))
            return
        
        # Handle option selection (1, 2, 3, one, two, three) - multi-language
        if self.pending_options:
            option_map = {
                # English
                "one": "1", "1": "1", "first": "1",
                "two": "2", "2": "2", "second": "2", 
                "three": "3", "3": "3", "third": "3",
                "four": "4", "4": "4", "fourth": "4",
                # Polish
                "jeden": "1", "pierwsza": "1", "pierwszą": "1", "pierwszy": "1",
                "dwa": "2", "druga": "2", "drugą": "2", "drugi": "2",
                "trzy": "3", "trzecia": "3", "trzecią": "3", "trzeci": "3",
                "cztery": "4", "czwarta": "4", "czwartą": "4", "czwarty": "4",
                # German
                "eins": "1", "erste": "1", "ersten": "1",
                "zwei": "2", "zweite": "2", "zweiten": "2",
                "drei": "3", "dritte": "3", "dritten": "3",
                "vier": "4", "vierte": "4", "vierten": "4",
            }
            choice = option_map.get(lower, lower)
            
            matched = False
            for key, desc, cmd in self.pending_options:
                if choice == key:
                    matched = True
                    self.pending_options = None
                    if cmd == "need_email":
                        # Use live narrator with track mode for better person detection
                        # Email is passed via SQ_NOTIFY_EMAIL env variable
                        self.pending_command_template = f"SQ_NOTIFY_EMAIL={{email}} sq live narrator --mode track --focus person --duration 60 --skip-checks --adaptive"
                        
                        # Check if email is already saved
                        saved_email = self.shell.context.get("email")
                        if saved_email:
                            # Offer to use saved email
                            self.pending_input_type = "use_saved_email"
                            await self.broadcast(Event(
                                type=EventType.TTS_SPEAK,
                                data={"text": f"I have your email saved as {saved_email}. Say 'yes' to use it, or 'new' to enter a different email."}
                            ))
                        else:
                            self.pending_input_type = "email"
                            await self.broadcast(Event(
                                type=EventType.TTS_SPEAK,
                                data={"text": "Please say your email address. You can spell it letter by letter."}
                            ))
                        return
                    elif cmd == "functions":
                        await self.broadcast(Event(
                            type=EventType.TTS_SPEAK,
                            data={"text": self.shell._list_functions()}
                        ))
                        return
                    else:
                        # Store selected command for confirmation
                        result = ShellResult(understood=True, shell_command=cmd, explanation=desc)
                        self.pending_command = result
                        
                        await self.broadcast(Event(
                            type=EventType.COMMAND_PARSED,
                            data={
                                "input": text,
                                "understood": True,
                                "explanation": desc,
                                "command": cmd,
                            }
                        ))
                        await self.broadcast(Event(
                            type=EventType.TTS_SPEAK,
                            data={"text": f"{desc}. Say yes to confirm."}
                        ))
                        return
            
            if not matched:
                # Check if this looks like a new command (not a number/option)
                # If so, clear pending options and process as new command
                all_option_words = set(option_map.keys())
                if choice not in all_option_words:
                    # User said something else - treat as new command
                    self.pending_options = None
                    # Fall through to process as new command (don't return)
                else:
                    # Invalid option number - repeat options (with cancel hint)
                    options_text = self.t.conv("say_cancel_anytime") + " "
                    for key, desc, _ in self.pending_options:
                        options_text += f"{key}: {desc}. "
                    await self.broadcast(Event(
                        type=EventType.TTS_SPEAK,
                        data={"text": options_text}
                    ))
                    return
        
        # Handle saved email confirmation
        if self.pending_input_type == "use_saved_email":
            saved_email = self.shell.context.get("email")
            
            # User wants to use saved email - execute immediately
            if lower in confirm_words:
                cmd = self.pending_command_template.replace("{email}", saved_email)
                result = ShellResult(understood=True, shell_command=cmd, explanation=f"Detect and email {saved_email}")
                self.pending_input_type = None
                self.pending_command_template = None
                
                await self.broadcast(Event(
                    type=EventType.CONTEXT_UPDATED,
                    data=self.shell.context
                ))
                
                await self.speak(self.t.conv("using_email", email=saved_email))
                
                # Execute command directly without requiring second confirmation
                await self.execute_command(result)
                return
            
            # User wants new email (multi-language)
            new_email_words = (
                "new", "different", "change", "other",  # English
                "nowy", "inny", "zmień", "zmien", "inna",  # Polish
                "neu", "andere", "ändern", "andern",  # German
            )
            if lower in reject_words or any(w in lower for w in new_email_words):
                self.pending_input_type = "email"
                await self.speak(self.t.conv("enter_new_email"))
                return
            
            # Check if user said something that looks like a new command
            # If it's not a simple yes/no/new, treat as new command
            if len(lower.split()) > 2 or any(cmd_word in lower for cmd_word in ("track", "śledź", "opisz", "describe", "read", "czytaj", "która", "godzina")):
                self.pending_input_type = None
                self.pending_command_template = None
                # Fall through to process as new command
            else:
                # Repeat question
                await self.speak(self.t.conv("say_yes_or_new", email=saved_email))
                return
        
        # Handle email input (spelling mode)
        if self.pending_input_type == "email":
            # Multi-language done/confirm words
            done_words = (
                "done", "confirm", "finished", "complete",  # English
                "gotowe", "koniec", "potwierdź", "zakończ",  # Polish
                "fertig", "bestätigen", "abgeschlossen",  # German
            )
            
            # Multi-language clear/reset words
            clear_words = (
                "clear", "reset", "start over", "again",  # English
                "wyczyść", "od nowa", "jeszcze raz", "reset",  # Polish
                "löschen", "neu", "nochmal",  # German
            )
            
            # Multi-language delete/backspace words
            delete_words = (
                "delete", "backspace", "remove", "undo",  # English
                "usuń", "cofnij", "skasuj",  # Polish
                "löschen", "entfernen", "zurück",  # German
            )
            
            # Check for done/confirm - execute immediately
            if any(w in lower for w in done_words):
                if self.spelling_buffer:
                    email = self.spelling_buffer.replace(" ", "").lower()
                    cmd = self.pending_command_template.replace("{email}", email)
                    result = ShellResult(understood=True, shell_command=cmd, explanation=f"Detect and email {email}")
                    self.pending_input_type = None
                    self.pending_command_template = None
                    self.spelling_buffer = ""
                    
                    # Save email to shell context and database
                    self.shell.context["email"] = email
                    self.db.set_config("email", email)
                    
                    # Broadcast context update to UI
                    await self.broadcast(Event(
                        type=EventType.CONTEXT_UPDATED,
                        data=self.shell.context
                    ))
                    
                    await self.speak(self.t.conv("email_set", email=email))
                    
                    # Execute command directly
                    await self.execute_command(result)
                    return
            
            # Check for corrections
            if any(w in lower for w in clear_words):
                self.spelling_buffer = ""
                await self.speak(self.t.conv("enter_new_email"))
                return
            
            # Check for delete/backspace
            if any(w in lower for w in delete_words):
                if self.spelling_buffer:
                    self.spelling_buffer = self.spelling_buffer[:-1]
                # Use simple response (no translation needed for buffer state)
                await self.broadcast(Event(
                    type=EventType.TTS_SPEAK,
                    data={"text": f"Current: {self.spelling_buffer or 'empty'}"}
                ))
                return
            
            # Check if user said something that looks like a new command
            command_keywords = (
                "track", "detect", "describe", "read", "watch", "stop", "help", "hello",  # English
                "śledź", "wykryj", "opisz", "czytaj", "która", "godzina", "cześć", "pomoc",  # Polish
                "verfolgen", "erkennen", "beschreiben", "lesen", "hallo", "hilfe",  # German
            )
            if any(cmd_word in lower for cmd_word in command_keywords):
                # User wants to do something else - clear email input and process as command
                self.pending_input_type = None
                self.pending_command_template = None
                self.spelling_buffer = ""
                # Fall through to process as new command
            else:
                # Handle @ and . symbols (multi-language)
                clean_text = text.lower()
                # English
                clean_text = clean_text.replace(" at ", "@").replace(" dot ", ".").replace("at sign", "@")
                # Polish
                clean_text = clean_text.replace("małpa", "@").replace("kropka", ".").replace(" małpa ", "@").replace(" kropka ", ".")
                # German
                clean_text = clean_text.replace("klammeraffe", "@").replace("punkt", ".").replace(" at ", "@")
                
                # If looks like full email, just use it
                if "@" in clean_text and "." in clean_text:
                    self.spelling_buffer = clean_text.replace(" ", "")
                    await self.broadcast(Event(
                        type=EventType.TTS_SPEAK,
                        data={"text": f"{self.spelling_buffer}. {self.t.conv('say_yes_confirm')}"}
                    ))
                    return
                
                # Add to buffer
                self.spelling_buffer += clean_text.replace(" ", "")
                await self.broadcast(Event(
                    type=EventType.TTS_SPEAK,
                    data={"text": f"{self.spelling_buffer}. {self.t.conv('say_cancel_anytime')}"}
                ))
                return
        
        # Parse with LLM shell
        result = self.shell.parse(text)
        
        # Handle special commands first (no broadcast needed)
        if result.function_name in ("help", "list", "history", "context", "set_url", "set_email"):
            await self.broadcast(Event(
                type=EventType.TTS_SPEAK,
                data={"text": result.explanation}
            ))
            return
        
        if result.function_name == "stop":
            await self.stop_process()
            return
        
        # Handle clarification with options (single broadcast with options)
        if result.function_name == "clarify" and result.options:
            self.pending_options = result.options
            options_text = result.explanation + " "
            for key, desc, _ in result.options:
                options_text += f"{key}: {desc}. "
            
            # Log options to session and database
            session = self.get_current_session()
            if session:
                question_line = f"❓ {result.explanation}"
                session.output.append(question_line)
                self.db.log_output(session.id, question_line, "system")
                for key, desc, _ in result.options:
                    opt_line = f"   {key}. {desc}"
                    session.output.append(opt_line)
                    self.db.log_output(session.id, opt_line, "system")
            
            await self.broadcast(Event(
                type=EventType.COMMAND_PARSED,
                data={
                    "input": text,
                    "understood": True,
                    "explanation": result.explanation,
                    "options": [(k, d) for k, d, _ in result.options],
                }
            ))
            await self.broadcast(Event(
                type=EventType.TTS_SPEAK,
                data={"text": options_text}
            ))
            return
        
        # Broadcast parsed result for other commands
        await self.broadcast(Event(
            type=EventType.COMMAND_PARSED,
            data={
                "input": text,
                "understood": result.understood,
                "explanation": result.explanation,
                "command": result.shell_command,
                "function": result.function_name,
            }
        ))
        
        # Handle need_input for email, etc.
        if result.function_name == "need_input":
            self.pending_input_type = result.input_type
            self.pending_command_template = result.pending_command
            
            await self.broadcast(Event(
                type=EventType.TTS_SPEAK,
                data={"text": result.explanation}
            ))
            return
        
        if not result.understood:
            await self.speak(self.t.conv("not_understood", text=text))
            return
        
        # Store pending command
        if result.shell_command:
            self.pending_command = result
            
            # Auto-inject URL from context
            missing, cmd = self.shell._check_missing_params(result.shell_command)
            
            if missing:
                # Ask for missing params
                await self.broadcast(Event(
                    type=EventType.TTS_SPEAK,
                    data={"text": f"Missing {', '.join(missing)}. Please provide the value."}
                ))
            else:
                # Speak the explanation and wait for confirm
                await self.broadcast(Event(
                    type=EventType.TTS_SPEAK,
                    data={"text": f"{result.explanation}. Say 'yes' to execute or 'no' to cancel."}
                ))
    
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
# WEB UI HTML
# =============================================================================

def get_voice_shell_html_from_template(ws_port: int, language: str = "en") -> str:
    """Load HTML from template files (new modular approach)."""
    import socket
    hostname = socket.gethostname()
    
    templates_dir = Path(__file__).parent / "templates"
    
    try:
        # Load template
        html_path = templates_dir / "voice_shell.html"
        css_path = templates_dir / "voice_shell.css"
        js_path = templates_dir / "voice_shell.js"
        
        if html_path.exists():
            html = html_path.read_text()
            
            # Replace placeholders
            html = html.replace("{{WS_HOST}}", "localhost")
            html = html.replace("{{WS_PORT}}", str(ws_port))
            html = html.replace("{{LANGUAGE}}", language)
            
            # Inline CSS and JS for simplicity
            if css_path.exists():
                css = css_path.read_text()
                html = html.replace(
                    '<link rel="stylesheet" href="/static/voice_shell.css">',
                    f'<style>{css}</style>'
                )
            
            if js_path.exists():
                js = js_path.read_text()
                # Remove CONFIG definition from JS (already defined in HTML template)
                import re
                js = re.sub(r'const CONFIG = \{[^}]+\};', '', js, flags=re.DOTALL)
                html = html.replace(
                    '<script src="/static/voice_shell.js"></script>',
                    f'<script>{js}</script>'
                )
            
            return html
    except Exception as e:
        print(f"Warning: Could not load template: {e}")
    
    # Fallback to inline HTML
    return get_voice_shell_html(ws_port)


def get_voice_shell_html(ws_port: int) -> str:
    """Generate the voice shell web UI HTML (inline fallback)."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Streamware Voice Shell</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            text-align: center;
            padding: 20px 0;
            border-bottom: 1px solid #333;
        }}
        h1 {{
            font-size: 2em;
            color: #4fc3f7;
        }}
        .status {{
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 10px;
            font-size: 0.9em;
        }}
        .status-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .status-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #666;
        }}
        .status-dot.connected {{ background: #4caf50; }}
        .status-dot.listening {{ background: #ff9800; animation: pulse 1s infinite; }}
        .status-dot.speaking {{ background: #2196f3; animation: pulse 0.5s infinite; }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .main {{
            display: grid;
            grid-template-columns: 250px 1fr 350px;
            gap: 20px;
            margin-top: 20px;
        }}
        @media (max-width: 1000px) {{
            .main {{ grid-template-columns: 1fr 1fr; }}
            .sessions-panel {{ display: none; }}
        }}
        @media (max-width: 700px) {{
            .main {{ grid-template-columns: 1fr; }}
        }}
        .sessions-panel {{
            max-height: 600px;
            overflow-y: auto;
        }}
        .session-item {{
            padding: 10px;
            margin: 5px 0;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            cursor: pointer;
            border-left: 3px solid #333;
        }}
        .session-item:hover {{ background: rgba(255,255,255,0.1); }}
        .session-item.active {{ border-left-color: #4fc3f7; background: rgba(79,195,247,0.1); }}
        .session-item.running {{ border-left-color: #ff9800; }}
        .session-item.completed {{ border-left-color: #4caf50; }}
        .session-item.error {{ border-left-color: #f44336; }}
        .session-name {{ font-weight: bold; font-size: 0.9em; }}
        .session-status {{ font-size: 0.75em; color: #888; }}
        .session-actions {{ display: flex; gap: 5px; margin-top: 5px; }}
        .session-actions button {{ 
            padding: 2px 8px; 
            font-size: 0.7em; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
        }}
        .btn-new-session {{
            width: 100%;
            padding: 10px;
            margin-bottom: 10px;
            background: #4fc3f7;
            color: black;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
        }}
        .btn-new-session:hover {{ background: #29b6f6; }}
        .panel {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
        }}
        .panel h2 {{
            font-size: 1.2em;
            color: #4fc3f7;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        #output {{
            height: 400px;
            overflow-y: auto;
            font-family: "Fira Code", monospace;
            font-size: 0.85em;
            background: #0d1117;
            padding: 15px;
            border-radius: 8px;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        .output-line {{
            margin: 2px 0;
            line-height: 1.4;
        }}
        .output-line.input {{ color: #58a6ff; }}
        .output-line.command {{ color: #7ee787; }}
        .output-line.error {{ color: #f85149; }}
        .output-line.tts {{ color: #d2a8ff; }}
        .output-line.system {{ color: #8b949e; }}
        .controls {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        .voice-btn {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 3px solid #4fc3f7;
            background: rgba(79, 195, 247, 0.1);
            color: #4fc3f7;
            font-size: 40px;
            cursor: pointer;
            transition: all 0.3s;
            margin: 0 auto;
        }}
        .voice-btn:hover {{
            background: rgba(79, 195, 247, 0.2);
            transform: scale(1.05);
        }}
        .voice-btn.listening {{
            background: rgba(255, 152, 0, 0.3);
            border-color: #ff9800;
            animation: pulse 1s infinite;
        }}
        .voice-btn.speaking {{
            background: rgba(33, 150, 243, 0.3);
            border-color: #2196f3;
        }}
        .text-input {{
            display: flex;
            gap: 10px;
        }}
        .text-input input {{
            flex: 1;
            padding: 12px 15px;
            border: 1px solid #333;
            border-radius: 8px;
            background: #0d1117;
            color: #e0e0e0;
            font-size: 1em;
        }}
        .text-input button {{
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            background: #4fc3f7;
            color: #000;
            font-weight: bold;
            cursor: pointer;
        }}
        .confirm-buttons {{
            display: flex;
            gap: 10px;
            justify-content: center;
        }}
        .confirm-buttons button {{
            padding: 10px 30px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
        }}
        .btn-yes {{ background: #4caf50; color: white; }}
        .btn-no {{ background: #f44336; color: white; }}
        .btn-stop {{ background: #ff9800; color: white; }}
        .btn-continuous {{ background: #333; color: #888; border: 1px solid #555; }}
        .btn-continuous.active {{ background: #2e7d32; color: white; border-color: #4caf50; }}
        .context {{
            background: #0d1117;
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 0.85em;
            margin-top: 15px;
        }}
        .context-item {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #333;
        }}
        .context-item:last-child {{ border-bottom: none; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎤 Streamware Voice Shell</h1>
            <div class="status">
                <div class="status-item">
                    <span class="status-dot" id="ws-status"></span>
                    <span id="ws-status-text">Connecting...</span>
                </div>
                <div class="status-item">
                    <span class="status-dot" id="voice-status"></span>
                    <span id="voice-status-text">Voice Ready</span>
                </div>
            </div>
        </header>
        
        <div class="main">
            <!-- Sessions Panel (left) -->
            <div class="panel sessions-panel">
                <h2>📋 Sessions</h2>
                <button class="btn-new-session" onclick="newSession()">➕ New Conversation</button>
                <div id="sessions-list"></div>
            </div>
            
            <!-- Shell Output (center) -->
            <div class="panel">
                <h2>
                    🖥️ Shell Output 
                    <span id="current-session-name" style="font-size: 0.7em; color: #888;"></span>
                    <button onclick="copyLogs()" style="float: right; font-size: 0.7em; padding: 4px 8px; cursor: pointer;" title="Copy logs">📋 Copy</button>
                    <button onclick="clearLogs()" style="float: right; font-size: 0.7em; padding: 4px 8px; cursor: pointer; margin-right: 5px;" title="Clear">🗑️ Clear</button>
                </h2>
                <div id="output"></div>
            </div>
            
            <!-- Voice Control (right) -->
            <div class="panel">
                <h2>🎤 Voice Control</h2>
                <div class="controls">
                    <button class="voice-btn" id="voice-btn" onclick="toggleVoice()">🎤</button>
                    <p style="text-align: center; color: #888;">Click or press Space to talk</p>
                    
                    <div class="text-input">
                        <input type="text" id="text-input" placeholder="Type a command..." 
                               onkeypress="if(event.key==='Enter')sendText()">
                        <button onclick="sendText()">Send</button>
                    </div>
                    
                    <div class="confirm-buttons" id="confirm-buttons" style="display:none;">
                        <button class="btn-yes" onclick="confirm()">✓ Yes</button>
                        <button class="btn-no" onclick="cancel()">✗ No</button>
                    </div>
                    
                    <div style="text-align: center; display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
                        <button class="btn-stop" onclick="stop()">⏹ Stop</button>
                        <button id="continuous-btn" class="btn-continuous active" onclick="toggleContinuous()">🔄 Continuous: ON</button>
                        <button id="bargein-btn" class="btn-continuous active" onclick="toggleBargeIn()">⚡ Barge-in: ON</button>
                    </div>
                    
                    <div class="context" id="context">
                        <div class="context-item">
                            <span>📹 URL:</span>
                            <span id="ctx-url">(not set)</span>
                        </div>
                        <div class="context-item">
                            <span>📧 Email:</span>
                            <span id="ctx-email">(not set)</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const WS_URL = "ws://" + window.location.hostname + ":{ws_port}";
        let ws;
        let recognition;
        let synthesis = window.speechSynthesis;
        let isListening = false;
        let pendingCommand = null;
        let currentSessionId = null;
        let sessions = {{}};
        
        // Session management
        function newSession() {{
            ws.send(JSON.stringify({{ type: 'new_session' }}));
            document.getElementById('output').innerHTML = '';
            addOutput('New conversation started. Say hello or a command.', 'system');
        }}
        
        function switchSession(sessionId) {{
            ws.send(JSON.stringify({{ type: 'switch_session', content: sessionId }}));
        }}
        
        function closeSession(sessionId) {{
            ws.send(JSON.stringify({{ type: 'close_session', content: sessionId }}));
        }}
        
        function updateSessionsList(sessionsList) {{
            const container = document.getElementById('sessions-list');
            container.innerHTML = '';
            sessions = {{}};
            
            sessionsList.forEach(s => {{
                sessions[s.id] = s;
                const div = document.createElement('div');
                div.className = 'session-item ' + s.status + (s.id === currentSessionId ? ' active' : '');
                div.setAttribute('data-session-id', s.id);
                div.innerHTML = `
                    <div class="session-name">${{s.name || 'Unnamed'}}</div>
                    <div class="session-status">${{s.status}} · ${{s.output_lines}} lines</div>
                    <div class="session-actions">
                        ${{s.status === 'running' ? '<button onclick="event.stopPropagation(); closeSession(\\'' + s.id + '\\')">⏹ Stop</button>' : ''}}
                        <button onclick="event.stopPropagation(); closeSession('` + s.id + `')">✕</button>
                    </div>
                `;
                div.addEventListener('click', function(e) {{
                    if (e.target.tagName !== 'BUTTON') {{
                        switchSession(s.id);
                    }}
                }});
                container.appendChild(div);
            }});
        }}
        
        function updateSessionInList(sessionId) {{
            // Update session status in UI
            const items = document.querySelectorAll('.session-item');
            items.forEach(item => {{
                if (item.dataset.sessionId === sessionId) {{
                    // Refresh from sessions object
                }}
            }});
        }}
        
        // Initialize WebSocket
        function connectWS() {{
            ws = new WebSocket(WS_URL);
            
            ws.onopen = () => {{
                document.getElementById('ws-status').classList.add('connected');
                document.getElementById('ws-status-text').textContent = 'Connected';
                addOutput('Connected to Streamware Voice Shell', 'system');
                // Request sessions list (new session will be created if none exist)
                ws.send(JSON.stringify({{ type: 'get_sessions' }}));
            }};
            
            ws.onclose = () => {{
                document.getElementById('ws-status').classList.remove('connected');
                document.getElementById('ws-status-text').textContent = 'Disconnected';
                setTimeout(connectWS, 3000);
            }};
            
            ws.onmessage = (event) => {{
                const data = JSON.parse(event.data);
                handleEvent(data);
            }};
        }}
        
        // Handle events from server
        function handleEvent(event) {{
            switch(event.type) {{
                case 'voice_input':
                case 'text_input':
                    addOutput('> ' + event.data.text, 'input');
                    break;
                    
                case 'command_parsed':
                    if (event.data.understood) {{
                        // Check if there are options to display
                        if (event.data.options && event.data.options.length > 0) {{
                            addOutput('❓ ' + event.data.explanation, 'system');
                            event.data.options.forEach(([key, desc]) => {{
                                addOutput('   ' + key + '. ' + desc, 'system');
                            }});
                        }} else {{
                            addOutput('✅ ' + event.data.explanation, 'system');
                            if (event.data.command) {{
                                addOutput('   Command: ' + event.data.command, 'command');
                                pendingCommand = event.data.command;
                                showConfirmButtons(true);
                            }}
                        }}
                    }} else {{
                        addOutput('❌ ' + event.data.explanation, 'error');
                    }}
                    break;
                    
                case 'command_executed':
                    addOutput('$ ' + event.data.command, 'command');
                    showConfirmButtons(false);
                    break;
                    
                case 'command_output':
                    addOutput(event.data.line, 'system');
                    break;
                
                case 'session_output':
                    // Output from a specific session
                    if (event.data.session_id === currentSessionId) {{
                        addOutput(event.data.line, 'system');
                    }}
                    updateSessionInList(event.data.session_id);
                    break;
                    
                case 'command_error':
                    addOutput('❌ Error: ' + event.data.error, 'error');
                    break;
                    
                case 'session_created':
                case 'session_closed':
                    updateSessionsList(event.data.sessions);
                    if (event.data.session) {{
                        currentSessionId = event.data.session.id;
                        document.getElementById('current-session-name').textContent = '(' + event.data.session.name + ')';
                    }}
                    break;
                    
                case 'session_switched':
                    currentSessionId = event.data.session.id;
                    document.getElementById('current-session-name').textContent = '(' + event.data.session.name + ')';
                    // Clear and show session output
                    document.getElementById('output').innerHTML = '';
                    if (event.data.output && event.data.output.length > 0) {{
                        event.data.output.forEach(line => {{
                            if (line) addOutput(line, 'system');
                        }});
                    }} else {{
                        addOutput('(No output yet)', 'system');
                    }}
                    // Update sessions list to show active
                    updateSessionsList(event.data.sessions || Object.values(sessions));
                    break;
                    
                case 'sessions_list':
                    updateSessionsList(event.data.sessions);
                    if (event.data.current) {{
                        currentSessionId = event.data.current;
                        // Update session name display
                        const currentSession = event.data.sessions.find(s => s.id === event.data.current);
                        if (currentSession) {{
                            document.getElementById('current-session-name').textContent = '(' + currentSession.name + ')';
                        }}
                    }}
                    // Show output from restored session
                    if (event.data.output && event.data.output.length > 0) {{
                        document.getElementById('output').innerHTML = '';
                        addOutput('📂 Restored conversation history:', 'system');
                        event.data.output.forEach(line => {{
                            if (line) addOutput(line, 'system');
                        }});
                    }}
                    break;
                    
                case 'command_completed':
                    addOutput('✓ Command completed', 'system');
                    break;
                    
                case 'command_cancel':
                    addOutput('✗ Cancelled', 'system');
                    showConfirmButtons(false);
                    break;
                    
                case 'tts_speak':
                    speak(event.data.text);
                    addOutput('🔊 ' + event.data.text, 'tts');
                    break;
                    
                case 'context_updated':
                    updateContext(event.data);
                    break;
            }}
        }}
        
        // Add output line
        function addOutput(text, type = 'system') {{
            const output = document.getElementById('output');
            const line = document.createElement('div');
            line.className = 'output-line ' + type;
            line.textContent = text;
            output.appendChild(line);
            output.scrollTop = output.scrollHeight;
        }}
        
        // Update context display
        function updateContext(ctx) {{
            document.getElementById('ctx-url').textContent = ctx.url || '(not set)';
            document.getElementById('ctx-email').textContent = ctx.email || '(not set)';
        }}
        
        // Copy logs to clipboard
        function copyLogs() {{
            const output = document.getElementById('output');
            const lines = Array.from(output.querySelectorAll('.output-line'))
                .map(el => el.textContent)
                .join('\\n');
            
            // Try clipboard API, fallback to execCommand
            if (navigator.clipboard && window.isSecureContext) {{
                navigator.clipboard.writeText(lines).then(() => {{
                    showCopyFeedback();
                }}).catch(() => {{ fallbackCopy(lines); }});
            }} else {{
                fallbackCopy(lines);
            }}
        }}
        
        function fallbackCopy(text) {{
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            try {{ document.execCommand('copy'); showCopyFeedback(); }}
            catch(e) {{ alert('Copy failed'); }}
            document.body.removeChild(ta);
        }}
        
        function showCopyFeedback() {{
            const btn = document.querySelector('[onclick="copyLogs()"]');
            if (btn) {{
                const orig = btn.textContent;
                btn.textContent = '✅ Copied!';
                setTimeout(() => {{ btn.textContent = orig; }}, 1500);
            }}
        }}
        
        // Clear logs
        function clearLogs() {{
            document.getElementById('output').innerHTML = '';
            addOutput('Output cleared', 'system');
        }}
        
        // Show/hide confirm buttons
        function showConfirmButtons(show) {{
            document.getElementById('confirm-buttons').style.display = show ? 'flex' : 'none';
        }}
        
        // Voice recognition
        function initVoice() {{
            if ('webkitSpeechRecognition' in window) {{
                recognition = new webkitSpeechRecognition();
                recognition.continuous = false;
                recognition.interimResults = true;  // Enable interim for faster barge-in
                recognition.lang = 'en-US';
                
                recognition.onstart = () => {{
                    isListening = true;
                    document.getElementById('voice-btn').classList.add('listening');
                    document.getElementById('voice-status').classList.add('listening');
                    document.getElementById('voice-status-text').textContent = isSpeaking ? 'Listening (while speaking)...' : 'Listening...';
                }};
                
                recognition.onend = () => {{
                    isListening = false;
                    document.getElementById('voice-btn').classList.remove('listening');
                    document.getElementById('voice-status').classList.remove('listening');
                    if (!isSpeaking) {{
                        document.getElementById('voice-status-text').textContent = 'Voice Ready';
                    }}
                }};
                
                recognition.onspeechstart = () => {{
                    // User started speaking - trigger barge-in
                    handleBargeIn();
                }};
                
                recognition.onresult = (event) => {{
                    const result = event.results[event.results.length - 1];
                    const text = result[0].transcript;
                    
                    // Only process final results
                    if (result.isFinal) {{
                        sendVoiceInput(text);
                    }} else if (bargeInMode && isSpeaking) {{
                        // Interim result while speaking - barge-in!
                        handleBargeIn();
                    }}
                }};
                
                recognition.onerror = (event) => {{
                    if (event.error !== 'no-speech') {{
                        console.error('Speech recognition error:', event.error);
                    }}
                    isListening = false;
                    document.getElementById('voice-btn').classList.remove('listening');
                }};
            }} else {{
                document.getElementById('voice-btn').disabled = true;
                document.getElementById('voice-status-text').textContent = 'Voice not supported';
            }}
        }}
        
        // Toggle voice listening
        function toggleVoice() {{
            if (isListening) {{
                recognition.stop();
            }} else {{
                recognition.start();
            }}
        }}
        
        // Send voice input
        function sendVoiceInput(text) {{
            // Check for yes/no confirmation
            const lower = text.toLowerCase();
            if (pendingCommand && (lower === 'yes' || lower === 'yeah' || lower === 'okay' || lower === 'execute')) {{
                confirm();
                return;
            }}
            if (pendingCommand && (lower === 'no' || lower === 'cancel' || lower === 'stop')) {{
                cancel();
                return;
            }}
            
            ws.send(JSON.stringify({{ type: 'voice_input', content: text }}));
        }}
        
        // Send text input
        function sendText() {{
            const input = document.getElementById('text-input');
            const text = input.value.trim();
            if (text) {{
                ws.send(JSON.stringify({{ type: 'text_input', content: text }}));
                input.value = '';
            }}
        }}
        
        // Confirm command
        function confirm() {{
            ws.send(JSON.stringify({{ type: 'confirm' }}));
            pendingCommand = null;
        }}
        
        // Cancel command
        function cancel() {{
            ws.send(JSON.stringify({{ type: 'cancel' }}));
            pendingCommand = null;
        }}
        
        // Stop running process
        function stop() {{
            ws.send(JSON.stringify({{ type: 'stop' }}));
        }}
        
        // Continuous mode - auto-listen after TTS
        let continuousMode = true;
        let bargeInMode = true;  // Allow interrupting TTS
        let isSpeaking = false;
        
        function toggleContinuous() {{
            continuousMode = !continuousMode;
            const btn = document.getElementById('continuous-btn');
            if (continuousMode) {{
                btn.classList.add('active');
                btn.textContent = '🔄 Continuous: ON';
            }} else {{
                btn.classList.remove('active');
                btn.textContent = '🔄 Continuous: OFF';
            }}
        }}
        
        function toggleBargeIn() {{
            bargeInMode = !bargeInMode;
            const btn = document.getElementById('bargein-btn');
            if (bargeInMode) {{
                btn.classList.add('active');
                btn.textContent = '⚡ Barge-in: ON';
            }} else {{
                btn.classList.remove('active');
                btn.textContent = '⚡ Barge-in: OFF';
            }}
        }}
        
        // Text-to-speech with barge-in support
        function speak(text) {{
            if (synthesis.speaking) {{
                synthesis.cancel();
            }}
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.1;  // Slightly faster
            utterance.pitch = 1.0;
            
            utterance.onstart = () => {{
                isSpeaking = true;
                document.getElementById('voice-btn').classList.add('speaking');
                document.getElementById('voice-status').classList.add('speaking');
                document.getElementById('voice-status-text').textContent = 'Speaking...';
                
                // In barge-in mode, start listening while speaking
                if (bargeInMode && recognition && !isListening) {{
                    try {{
                        recognition.start();
                    }} catch(e) {{}}
                }}
            }};
            
            utterance.onend = () => {{
                isSpeaking = false;
                document.getElementById('voice-btn').classList.remove('speaking');
                document.getElementById('voice-status').classList.remove('speaking');
                document.getElementById('voice-status-text').textContent = 'Voice Ready';
                
                // Auto-listen in continuous mode (if not already listening from barge-in)
                if (continuousMode && recognition && !isListening) {{
                    setTimeout(() => {{
                        if (!isListening) {{
                            try {{
                                recognition.start();
                            }} catch(e) {{}}
                        }}
                    }}, 300);
                }}
            }};
            
            synthesis.speak(utterance);
        }}
        
        // Cancel TTS when user speaks (barge-in)
        function handleBargeIn() {{
            if (bargeInMode && isSpeaking) {{
                synthesis.cancel();
                isSpeaking = false;
                document.getElementById('voice-btn').classList.remove('speaking');
                document.getElementById('voice-status-text').textContent = 'Listening (interrupted)';
                addOutput('⚡ [Barge-in: TTS interrupted]', 'system');
            }}
        }}
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {{
            if (e.code === 'Space' && document.activeElement.tagName !== 'INPUT') {{
                e.preventDefault();
                toggleVoice();
            }}
        }});
        
        // Initialize
        connectWS();
        initVoice();
    </script>
</body>
</html>'''


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
