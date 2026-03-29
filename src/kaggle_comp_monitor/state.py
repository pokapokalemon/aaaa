from __future__ import annotations

import sqlite3
from pathlib import Path


class StateDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self._init_db()

    def _init_db(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_items (
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                created_at TEXT,
                url TEXT,
                PRIMARY KEY (item_type, item_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_started_at TEXT PRIMARY KEY,
                competition_slug TEXT NOT NULL,
                discussion_count INTEGER NOT NULL,
                code_count INTEGER NOT NULL
            )
            """
        )
        self.conn.commit()

    def has_seen(self, item_type: str, item_id: str) -> bool:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT 1 FROM seen_items WHERE item_type = ? AND item_id = ? LIMIT 1",
            (item_type, item_id),
        )
        return cur.fetchone() is not None

    def mark_seen(self, item_type: str, item_id: str, created_at: str, url: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO seen_items(item_type, item_id, created_at, url) VALUES (?, ?, ?, ?)",
            (item_type, item_id, created_at, url),
        )
        self.conn.commit()

    def mark_many_seen(self, item_type: str, items: list[tuple[str, str, str]]) -> None:
        if not items:
            return
        cur = self.conn.cursor()
        cur.executemany(
            "INSERT OR IGNORE INTO seen_items(item_type, item_id, created_at, url) VALUES (?, ?, ?, ?)",
            [(item_type, item_id, created_at, url) for item_id, created_at, url in items],
        )
        self.conn.commit()

    def get_seen_ids(self, item_type: str) -> set[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT item_id FROM seen_items WHERE item_type = ?", (item_type,))
        return {str(row[0]) for row in cur.fetchall()}

    def log_run(self, started_at: str, competition_slug: str, discussion_count: int, code_count: int) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO runs(run_started_at, competition_slug, discussion_count, code_count) VALUES (?, ?, ?, ?)",
            (started_at, competition_slug, discussion_count, code_count),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
