"""Explicit, local-only memory for user-approved TIRIAS facts.

No conversation is automatically persisted. Call remember() only after the
user explicitly asks TIRIAS to remember a non-sensitive preference or fact.
"""
from contextlib import contextmanager
from pathlib import Path
import sqlite3


class LocalMemory:
    def __init__(self, database_path):
        self.database_path = Path(database_path).expanduser()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS memories (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=5)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _validate(key, value):
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("Memory key and value must be text.")
        key, value = key.strip(), value.strip()
        if not key or len(key) > 80 or not value or len(value) > 500:
            raise ValueError("Memory key must be 1–80 characters and value 1–500 characters.")
        if any(ord(char) < 32 for char in key + value):
            raise ValueError("Memory cannot contain control characters.")
        return key, value

    def remember(self, key, value):
        key, value = self._validate(key, value)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO memories(key, value, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(key) DO UPDATE SET
                     value=excluded.value, updated_at=CURRENT_TIMESTAMP""",
                (key, value),
            )

    def recall(self, key):
        if not isinstance(key, str):
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM memories WHERE key = ?", (key.strip(),)
            ).fetchone()
        return row[0] if row else None

    def forget(self, key):
        if not isinstance(key, str):
            return False
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM memories WHERE key = ?", (key.strip(),)
            )
        return cursor.rowcount > 0

    def list_keys(self):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT key FROM memories ORDER BY key COLLATE NOCASE"
            ).fetchall()
        return [row[0] for row in rows]
