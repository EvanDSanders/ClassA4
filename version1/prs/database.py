"""SQLite persistence layer."""
import sqlite3


class Database:
    def __init__(self, path="prs.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS patients (
            patient_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT,
            birthday TEXT,
            phone TEXT
        );
        CREATE TABLE IF NOT EXISTS visit_notes (
            note_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL REFERENCES patients(patient_id),
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            category TEXT,
            category_status TEXT NOT NULL DEFAULT 'none'
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT DEFAULT CURRENT_TIMESTAMP,
            username TEXT,
            action TEXT,
            detail TEXT
        );
        """)
        self.conn.commit()

    def execute(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def query(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def close(self):
        self.conn.close()
