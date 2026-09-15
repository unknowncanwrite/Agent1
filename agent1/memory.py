"""3-layer memory that beats single-store agents.

- Short-term: in-context rolling buffer (handled by agent loop).
- Long-term: SQLite facts with LIKE search (no vector dep needed).
- Episodic: append-only markdown log of completed tasks.
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path


class Memory:
    def __init__(self, path: str = "./workspace/.trace/memory.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS facts "
                        "(id INTEGER PRIMARY KEY, ts REAL, topic TEXT, fact TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS episodes "
                        "(id INTEGER PRIMARY KEY, ts REAL, task TEXT, summary TEXT)")
        self.db.commit()

    def save_fact(self, fact: str, topic: str = "general"):
        self.db.execute("INSERT INTO facts (ts, topic, fact) VALUES (?,?,?)",
                        (time.time(), topic, fact))
        self.db.commit()

    def search(self, query: str, limit: int = 8) -> list[tuple[str, str]]:
        words = [w for w in query.lower().split() if len(w) > 2][:6]
        if not words:
            rows = self.db.execute(
                "SELECT topic, fact FROM facts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [(t, f) for t, f in rows]
        where = " OR ".join("lower(fact) LIKE ? OR lower(topic) LIKE ?" for _ in words)
        params: list = []
        for w in words:
            params += [f"%{w}%", f"%{w}%"]
        rows = self.db.execute(
            f"SELECT topic, fact FROM facts WHERE {where} ORDER BY id DESC LIMIT ?",
            (*params, limit)).fetchall()
        return [(t, f) for t, f in rows]

    def save_episode(self, task: str, summary: str):
        self.db.execute("INSERT INTO episodes (ts, task, summary) VALUES (?,?,?)",
                        (time.time(), task, summary))
        self.db.commit()
        log = self.path.parent / "episodes.md"
        with open(log, "a") as f:
            f.write(f"\n## {time.strftime('%Y-%m-%d %H:%M')} — {task[:120]}\n{summary[:2000]}\n")

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass
