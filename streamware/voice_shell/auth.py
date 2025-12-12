"""
Email-based Magic Link Authentication for Voice Shell

Simple authentication via email magic links:
1. User enters email
2. Server sends magic link with token
3. User clicks link → logged in with session cookie

This works on localhost too (for development/testing).
"""

import hashlib
import hmac
import logging
import secrets
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Token expiry in seconds (15 minutes for magic links)
MAGIC_LINK_EXPIRY = 15 * 60
# Session expiry in days
SESSION_EXPIRY_DAYS = 30

# Secret key for signing (generated once, stored in DB)
_secret_key: Optional[str] = None


@dataclass
class User:
    """User record."""
    id: str
    email: str
    created_at: datetime
    last_login: Optional[datetime] = None


@dataclass
class Session:
    """User session."""
    token: str
    user_id: str
    created_at: datetime
    expires_at: datetime


class AuthDB:
    """SQLite database for authentication."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path.home() / ".streamware" / "auth.db")
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database tables."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS magic_links (
                    token TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    used INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id TEXT PRIMARY KEY,
                    panel_positions TEXT,  -- JSON
                    language TEXT DEFAULT 'en',
                    theme TEXT DEFAULT 'dark',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_magic_links_email ON magic_links(email);
            """)
            conn.commit()
        finally:
            conn.close()
    
    def get_secret_key(self) -> str:
        """Get or create secret key for signing tokens."""
        global _secret_key
        if _secret_key:
            return _secret_key
        
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT value FROM config WHERE key = 'secret_key'"
            ).fetchone()
            
            if row:
                _secret_key = row['value']
            else:
                _secret_key = secrets.token_hex(32)
                conn.execute(
                    "INSERT INTO config (key, value) VALUES ('secret_key', ?)",
                    (_secret_key,)
                )
                conn.commit()
            
            return _secret_key
        finally:
            conn.close()
    
    # -------------------------------------------------------------------------
    # Magic Links
    # -------------------------------------------------------------------------
    
    def create_magic_link(self, email: str) -> str:
        """Create a magic link token for email.
        
        Returns:
            token: The magic link token to be sent via email
        """
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(seconds=MAGIC_LINK_EXPIRY)
        
        conn = self._get_conn()
        try:
            # Delete old unused tokens for this email
            conn.execute(
                "DELETE FROM magic_links WHERE email = ? AND used = 0",
                (email,)
            )
            
            conn.execute(
                "INSERT INTO magic_links (token, email, expires_at) VALUES (?, ?, ?)",
                (token, email.lower(), expires_at)
            )
            conn.commit()
            return token
        finally:
            conn.close()
    
    def verify_magic_link(self, token: str) -> Optional[str]:
        """Verify magic link token.
        
        Returns:
            email if valid, None otherwise
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT email, expires_at, used FROM magic_links 
                   WHERE token = ?""",
                (token,)
            ).fetchone()
            
            if not row:
                return None
            
            if row['used']:
                return None
            
            expires_at = datetime.fromisoformat(row['expires_at'])
            if datetime.now() > expires_at:
                return None
            
            # Mark as used
            conn.execute(
                "UPDATE magic_links SET used = 1 WHERE token = ?",
                (token,)
            )
            conn.commit()
            
            return row['email']
        finally:
            conn.close()
    
    # -------------------------------------------------------------------------
    # Users
    # -------------------------------------------------------------------------
    
    def get_or_create_user(self, email: str) -> User:
        """Get existing user or create new one."""
        email = email.lower()
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()
            
            if row:
                return User(
                    id=row['id'],
                    email=row['email'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None
                )
            
            # Create new user
            user_id = secrets.token_hex(16)
            conn.execute(
                "INSERT INTO users (id, email) VALUES (?, ?)",
                (user_id, email)
            )
            conn.commit()
            
            return User(
                id=user_id,
                email=email,
                created_at=datetime.now()
            )
        finally:
            conn.close()
    
    def update_last_login(self, user_id: str):
        """Update user's last login time."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now(), user_id)
            )
            conn.commit()
        finally:
            conn.close()
    
    # -------------------------------------------------------------------------
    # Sessions
    # -------------------------------------------------------------------------
    
    def create_session(self, user_id: str) -> str:
        """Create session for user.
        
        Returns:
            session token
        """
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=SESSION_EXPIRY_DAYS)
        
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                (token, user_id, expires_at)
            )
            conn.commit()
            return token
        finally:
            conn.close()
    
    def verify_session(self, token: str) -> Optional[User]:
        """Verify session token.
        
        Returns:
            User if valid session, None otherwise
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT s.user_id, s.expires_at, u.email, u.created_at, u.last_login
                   FROM sessions s
                   JOIN users u ON s.user_id = u.id
                   WHERE s.token = ?""",
                (token,)
            ).fetchone()
            
            if not row:
                return None
            
            expires_at = datetime.fromisoformat(row['expires_at'])
            if datetime.now() > expires_at:
                # Session expired, delete it
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                return None
            
            return User(
                id=row['user_id'],
                email=row['email'],
                created_at=datetime.fromisoformat(row['created_at']),
                last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None
            )
        finally:
            conn.close()
    
    def delete_session(self, token: str):
        """Delete session (logout)."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        finally:
            conn.close()
    
    # -------------------------------------------------------------------------
    # User Settings (grid positions, etc.)
    # -------------------------------------------------------------------------
    
    def get_user_settings(self, user_id: str) -> dict:
        """Get user settings."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM user_settings WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if not row:
                return {"language": "en", "theme": "dark", "panel_positions": None}
            
            import json
            return {
                "language": row['language'],
                "theme": row['theme'],
                "panel_positions": json.loads(row['panel_positions']) if row['panel_positions'] else None
            }
        finally:
            conn.close()
    
    def save_user_settings(self, user_id: str, settings: dict):
        """Save user settings."""
        import json
        
        conn = self._get_conn()
        try:
            panel_positions = json.dumps(settings.get('panel_positions')) if settings.get('panel_positions') else None
            
            conn.execute("""
                INSERT INTO user_settings (user_id, panel_positions, language, theme, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    panel_positions = excluded.panel_positions,
                    language = excluded.language,
                    theme = excluded.theme,
                    updated_at = excluded.updated_at
            """, (
                user_id,
                panel_positions,
                settings.get('language', 'en'),
                settings.get('theme', 'dark'),
                datetime.now()
            ))
            conn.commit()
        finally:
            conn.close()


# Global auth database instance
_auth_db: Optional[AuthDB] = None


def get_auth_db() -> AuthDB:
    """Get global auth database instance."""
    global _auth_db
    if _auth_db is None:
        _auth_db = AuthDB()
    return _auth_db


# -------------------------------------------------------------------------
# Email sending
# -------------------------------------------------------------------------

def send_magic_link_email(email: str, base_url: str = "http://localhost:9876") -> bool:
    """Send magic link email.
    
    Args:
        email: User's email address
        base_url: Base URL for the magic link (default: localhost)
    
    Returns:
        True if sent successfully
    """
    db = get_auth_db()
    token = db.create_magic_link(email)
    
    magic_link = f"{base_url}/auth/verify?token={token}"
    
    # For localhost testing, just print the link
    if "localhost" in base_url or "127.0.0.1" in base_url:
        print(f"\n🔐 Magic Link for {email}:")
        print(f"   {magic_link}")
        print(f"   (Valid for {MAGIC_LINK_EXPIRY // 60} minutes)\n")
        return True
    
    # For production, send actual email
    try:
        from ..components.email import EmailComponent
        
        email_component = EmailComponent(f"email://send?to={email}")
        result = email_component.process({
            "subject": "🔐 Streamware Voice Shell - Login Link",
            "body": f"""
Hello!

Click the link below to log in to Streamware Voice Shell:

{magic_link}

This link is valid for {MAGIC_LINK_EXPIRY // 60} minutes.

If you didn't request this login, you can ignore this email.

Best,
Streamware Team
            """.strip()
        })
        
        return result.get("success", False)
    except Exception as e:
        logger.error(f"Failed to send magic link email: {e}")
        # Fallback: print to console
        print(f"\n🔐 Magic Link for {email}:")
        print(f"   {magic_link}")
        return True


def verify_magic_link_token(token: str) -> Tuple[Optional[User], Optional[str]]:
    """Verify magic link token and create session.
    
    Returns:
        (User, session_token) if valid, (None, None) otherwise
    """
    db = get_auth_db()
    
    email = db.verify_magic_link(token)
    if not email:
        return None, None
    
    user = db.get_or_create_user(email)
    db.update_last_login(user.id)
    
    session_token = db.create_session(user.id)
    
    return user, session_token
