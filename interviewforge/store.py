"""SQLite persistence for interview sessions and per-question scores."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    topic_filter TEXT,
    difficulty_filter TEXT,
    duration_s INTEGER NOT NULL DEFAULT 0,
    question_count INTEGER NOT NULL DEFAULT 0,
    avg_score REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    question_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    answer_text TEXT NOT NULL DEFAULT '',
    score INTEGER NOT NULL DEFAULT 0,
    time_used_s REAL NOT NULL DEFAULT 0,
    timed_out INTEGER NOT NULL DEFAULT 0,
    key_points_covered INTEGER NOT NULL DEFAULT 0,
    key_points_total INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_answers_session ON answers(session_id);
CREATE INDEX IF NOT EXISTS idx_answers_topic ON answers(topic);
"""


def default_db_path() -> Path:
    override = os.environ.get("INTERVIEWFORGE_DB")
    if override:
        return Path(override).expanduser()
    data_home = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(data_home) / "interviewforge" / "interviewforge.db"


class Store:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # -- writes ---------------------------------------------------------
    def create_session(self, topic_filter=None, difficulty_filter=None) -> int:
        cur = self.conn.execute(
            "INSERT INTO sessions (started_at, topic_filter, difficulty_filter) VALUES (?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), topic_filter, difficulty_filter),
        )
        self.conn.commit()
        return cur.lastrowid

    def record_answer(
        self,
        session_id: int,
        question_id: str,
        topic: str,
        difficulty: str,
        answer_text: str,
        score: int,
        time_used_s: float,
        timed_out: bool,
        key_points_covered: int,
        key_points_total: int,
    ) -> None:
        self.conn.execute(
            """INSERT INTO answers
               (session_id, question_id, topic, difficulty, answer_text, score,
                time_used_s, timed_out, key_points_covered, key_points_total)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id, question_id, topic, difficulty, answer_text, score,
                time_used_s, int(timed_out), key_points_covered, key_points_total,
            ),
        )
        self.conn.commit()

    def finalize_session(self, session_id: int, duration_s: float) -> None:
        row = self.conn.execute(
            "SELECT AVG(score) AS avg_score, COUNT(*) AS n FROM answers WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        self.conn.execute(
            "UPDATE sessions SET duration_s = ?, question_count = ?, avg_score = ? WHERE id = ?",
            (int(duration_s), row["n"], round(row["avg_score"] or 0, 1), session_id),
        )
        self.conn.commit()

    # -- reads ----------------------------------------------------------
    def list_sessions(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def session_answers(self, session_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM answers WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_session(self, session_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None

    def topic_aggregates(self, session_id: int | None = None) -> list[dict]:
        """Average score per topic — for one session, or across all sessions."""
        if session_id is None:
            where, params = "", ()
        else:
            where, params = "WHERE session_id = ?", (session_id,)
        rows = self.conn.execute(
            f"""SELECT topic, COUNT(*) AS n, ROUND(AVG(score), 1) AS avg_score,
                       MIN(score) AS min_score, MAX(score) AS max_score
                FROM answers {where} GROUP BY topic ORDER BY avg_score""",
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    def previous_session_id(self, session_id: int) -> int | None:
        row = self.conn.execute(
            "SELECT id FROM sessions WHERE id < ? ORDER BY id DESC LIMIT 1", (session_id,)
        ).fetchone()
        return row["id"] if row else None
