"""
SQLite database for Voice Shell persistence.

Stores:
- User configuration (email, URL, preferences)
- Session history and logs
- Command history
- Context state
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict


# Default database path
DEFAULT_DB_PATH = Path.home() / ".streamware" / "voice_shell.db"


@dataclass
class SessionRecord:
    """Record of a voice shell session."""
    id: str
    name: str
    created_at: str
    ended_at: Optional[str] = None
    status: str = "active"
    command_count: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CommandRecord:
    """Record of a command execution."""
    id: int
    session_id: str
    timestamp: str
    user_input: str
    parsed_command: Optional[str] = None
    explanation: Optional[str] = None
    executed: bool = False
    result: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConfigRecord:
    """User configuration record."""
    key: str
    value: str
    updated_at: str
    
    def to_dict(self) -> dict:
        return asdict(self)


class VoiceShellDB:
    """SQLite database for Voice Shell persistence."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- User configuration (email, URL, preferences)
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                
                -- Sessions
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT DEFAULT 'active',
                    command_count INTEGER DEFAULT 0
                );
                
                -- Commands executed
                CREATE TABLE IF NOT EXISTS commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    parsed_command TEXT,
                    explanation TEXT,
                    executed INTEGER DEFAULT 0,
                    result TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
                
                -- Session logs (output lines)
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TEXT NOT NULL,
                    level TEXT DEFAULT 'info',
                    message TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
                
                -- Context variables per session
                CREATE TABLE IF NOT EXISTS context (
                    session_id TEXT,
                    key TEXT,
                    value TEXT,
                    PRIMARY KEY (session_id, key),
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
                
                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_commands_session ON commands(session_id);
                CREATE INDEX IF NOT EXISTS idx_logs_session ON logs(session_id);
                CREATE INDEX IF NOT EXISTS idx_context_session ON context(session_id);
            """)
            conn.commit()
    
    # =========================================================================
    # Configuration
    # =========================================================================
    
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        now = datetime.now().isoformat()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value_str, now))
            conn.commit()
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM config WHERE key = ?", (key,)
            ).fetchone()
            
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
            return default
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration values."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT key, value FROM config").fetchall()
            
            result = {}
            for key, value in rows:
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value
            return result
    
    # =========================================================================
    # Sessions
    # =========================================================================
    
    def create_session(self, session_id: str, name: str) -> SessionRecord:
        """Create a new session record (or update if exists)."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions (id, name, created_at, status)
                VALUES (?, ?, ?, 'active')
            """, (session_id, name, now))
            conn.commit()
        
        return SessionRecord(id=session_id, name=name, created_at=now)
    
    def end_session(self, session_id: str, status: str = "completed") -> None:
        """Mark a session as ended."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions SET ended_at = ?, status = ?
                WHERE id = ?
            """, (now, status, session_id))
            conn.commit()
    
    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """Get a session by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            
            if row:
                return SessionRecord(**dict(row))
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its related data."""
        with sqlite3.connect(self.db_path) as conn:
            # Delete logs (table is 'logs', not 'output_logs')
            conn.execute("DELETE FROM logs WHERE session_id = ?", (session_id,))
            # Delete commands
            conn.execute("DELETE FROM commands WHERE session_id = ?", (session_id,))
            # Delete context
            conn.execute("DELETE FROM context WHERE session_id = ?", (session_id,))
            # Delete session
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            return True
    
    def get_recent_sessions(self, limit: int = 10) -> List[SessionRecord]:
        """Get recent sessions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM sessions 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [SessionRecord(**dict(row)) for row in rows]
    
    # =========================================================================
    # Commands
    # =========================================================================
    
    def log_command(
        self,
        session_id: str,
        user_input: str,
        parsed_command: Optional[str] = None,
        explanation: Optional[str] = None,
        executed: bool = False,
        result: Optional[str] = None
    ) -> int:
        """Log a command execution."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO commands 
                (session_id, timestamp, user_input, parsed_command, explanation, executed, result)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, now, user_input, parsed_command, explanation, int(executed), result))
            
            # Update command count
            conn.execute("""
                UPDATE sessions SET command_count = command_count + 1
                WHERE id = ?
            """, (session_id,))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_session_commands(self, session_id: str) -> List[CommandRecord]:
        """Get all commands for a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM commands WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,)).fetchall()
            
            return [CommandRecord(**dict(row)) for row in rows]
    
    def get_recent_commands(self, limit: int = 50) -> List[CommandRecord]:
        """Get recent commands across all sessions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM commands 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [CommandRecord(**dict(row)) for row in rows]
    
    # =========================================================================
    # Logs
    # =========================================================================
    
    def log_output(self, session_id: str, message: str, level: str = "info") -> None:
        """Log an output line."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO logs (session_id, timestamp, level, message)
                VALUES (?, ?, ?, ?)
            """, (session_id, now, level, message))
            conn.commit()
    
    def get_session_logs(self, session_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get logs for a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM logs WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (session_id, limit)).fetchall()
            
            return [dict(row) for row in rows]
    
    # =========================================================================
    # Context
    # =========================================================================
    
    def set_context(self, session_id: str, key: str, value: Any) -> None:
        """Set a context variable for a session."""
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO context (session_id, key, value)
                VALUES (?, ?, ?)
            """, (session_id, key, value_str))
            conn.commit()
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """Get all context for a session."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT key, value FROM context WHERE session_id = ?
            """, (session_id,)).fetchall()
            
            result = {}
            for key, value in rows:
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value
            return result
    
    # =========================================================================
    # Utilities
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            stats["total_sessions"] = conn.execute(
                "SELECT COUNT(*) FROM sessions"
            ).fetchone()[0]
            
            stats["total_commands"] = conn.execute(
                "SELECT COUNT(*) FROM commands"
            ).fetchone()[0]
            
            stats["total_logs"] = conn.execute(
                "SELECT COUNT(*) FROM logs"
            ).fetchone()[0]
            
            stats["config_entries"] = conn.execute(
                "SELECT COUNT(*) FROM config"
            ).fetchone()[0]
            
            stats["db_path"] = str(self.db_path)
            stats["db_size_kb"] = round(self.db_path.stat().st_size / 1024, 1)
            
            return stats


# Singleton instance
_db_instance: Optional[VoiceShellDB] = None


def get_db() -> VoiceShellDB:
    """Get the database singleton instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = VoiceShellDB()
    return _db_instance
