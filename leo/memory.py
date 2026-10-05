from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


class StudentMemory:
    """Small local persistent memory store; no external database or API."""

    def __init__(self, db_path: str | None = None):
        path = db_path or os.getenv("LEO_DB_PATH", "./data/leo_memory.db")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS student_memory (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    student_name TEXT NOT NULL,
                    last_topic TEXT,
                    topics_json TEXT NOT NULL DEFAULT '[]',
                    sessions INTEGER NOT NULL DEFAULT 0
                )"""
            )
            conn.commit()

    def get(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT student_name,last_topic,topics_json,sessions FROM student_memory WHERE id=1"
            ).fetchone()
        if not row:
            return {"student_name": "Student", "last_topic": "", "topics": [], "sessions": 0}
        return {
            "student_name": row[0],
            "last_topic": row[1] or "",
            "topics": json.loads(row[2] or "[]"),
            "sessions": row[3],
        }

    def update(self, student_name: str, topic: str):
        current = self.get()
        topics = current["topics"]
        if topic and topic not in topics:
            topics.append(topic)
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO student_memory(id,student_name,last_topic,topics_json,sessions)
                   VALUES(1,?,?,?,1)
                   ON CONFLICT(id) DO UPDATE SET
                     student_name=excluded.student_name,
                     last_topic=excluded.last_topic,
                     topics_json=excluded.topics_json,
                     sessions=student_memory.sessions+1""",
                (student_name or current["student_name"], topic, json.dumps(topics)),
            )
            conn.commit()

    def context(self) -> str:
        m = self.get()
        return (
            f"Student name: {m['student_name']}\n"
            f"Previous topic: {m['last_topic'] or 'none'}\n"
            f"Topics studied: {', '.join(m['topics'][-8:]) or 'none'}\n"
            f"Completed sessions: {m['sessions']}"
        )
