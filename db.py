#!/usr/bin/env python3
"""db.py — SQLite cache for GPU Fleet Monitor."""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = ROOT / "fleet.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS instances (
  project_key   TEXT NOT NULL,
  name          TEXT NOT NULL,
  instance_id   TEXT,
  zone          TEXT,
  machine_type  TEXT,
  status        TEXT,
  last_start    TEXT,
  status_message TEXT,
  rack          TEXT,
  collected_at  TEXT,
  PRIMARY KEY (project_key, name)
);
CREATE INDEX IF NOT EXISTS idx_instances_project ON instances(project_key);

CREATE TABLE IF NOT EXISTS log_events (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  project_key  TEXT,
  instance     TEXT,
  event_type   TEXT,
  severity     TEXT,
  message      TEXT,
  timestamp    TEXT,
  log_name     TEXT
);
CREATE INDEX IF NOT EXISTS idx_logs_instance ON log_events(project_key, instance);
"""


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.executescript(SCHEMA)


def save_instances(project_key: str, instances: list[dict], collected_at: str):
    with _conn() as c:
        c.execute("DELETE FROM instances WHERE project_key=?", (project_key,))
        for i in instances:
            c.execute("""
                INSERT OR REPLACE INTO instances
                  (project_key,name,instance_id,zone,machine_type,status,
                   last_start,status_message,rack,collected_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (project_key, i["name"], i.get("instance_id"), i.get("zone"),
                  i.get("machine_type"), i.get("status"), i.get("last_start"),
                  i.get("status_message"), i.get("rack"), collected_at))


def get_instances(project_key: str) -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM instances WHERE project_key=? ORDER BY name",
            (project_key,))]


def get_instance(project_key: str, name: str) -> dict | None:
    with _conn() as c:
        r = c.execute(
            "SELECT * FROM instances WHERE project_key=? AND name=?",
            (project_key, name)).fetchone()
        return dict(r) if r else None


def get_logs(project_key: str, instance: str, limit: int = 200) -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute(
            """SELECT * FROM log_events WHERE project_key=? AND instance=?
               ORDER BY timestamp DESC LIMIT ?""",
            (project_key, instance, limit))]
