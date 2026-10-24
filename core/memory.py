"""Persistent memory system for TARS."""
import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union


class MemoryStore:
    """Manages short-term conversation context and persistent long-term knowledge."""

    def __init__(self, db_path: Optional[Union[Path, str]] = None):
        if db_path is None:
            db_path = str(Path(__file__).resolve().parent.parent / "memory.db")
        else:
            db_path = str(db_path)
            
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        """Initializes SQLite tables for messages and key-value preferences."""
        with self._conn:
            cursor = self._conn.cursor()
            # Conversation logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    role TEXT,
                    content TEXT,
                    tool_calls TEXT
                )
            """)
            # Long-term key-value user memories
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_memories (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at REAL
                )
            """)

    def add_message(self, role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
        """Appends a message to the conversation history."""
        with self._conn:
            cursor = self._conn.cursor()
            cursor.execute(
                "INSERT INTO conversation_history (timestamp, role, content, tool_calls) VALUES (?, ?, ?, ?)",
                (time.time(), role, content, json.dumps(tool_calls or []))
            )

    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves the most recent messages for LLM context."""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT role, content, tool_calls FROM conversation_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()

        messages = []
        for role, content, tool_calls_json in reversed(rows):
            messages.append({
                "role": role,
                "content": content,
                "tool_calls": json.loads(tool_calls_json or "[]")
            })
        return messages

    def set_user_preference(self, key: str, value: Any) -> None:
        """Stores a persistent user preference or learned fact."""
        with self._conn:
            cursor = self._conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO user_memories (key, value, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time())
            )

    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Retrieves a persistent user preference."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT value FROM user_memories WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                return row[0]
        return default

    def get_all_preferences(self) -> Dict[str, Any]:
        """Returns all persistent memories."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT key, value FROM user_memories")
        rows = cursor.fetchall()
        result = {}
        for k, v in rows:
            try:
                result[k] = json.loads(v)
            except Exception:
                result[k] = v
        return result

    def clear_history(self) -> None:
        """Clears short-term conversation history while keeping preferences."""
        with self._conn:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM conversation_history")

    def close(self) -> None:
        """Closes the database connection."""
        if self._conn:
            self._conn.close()
