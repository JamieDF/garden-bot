import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import settings
from .models import ReadingCreate


def init_db() -> None:
    """Initialize the database schema."""
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                sensor TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_timestamp
            ON readings(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_sensor
            ON readings(sensor)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                kind TEXT NOT NULL,
                data TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_journal_timestamp
            ON agent_journal(timestamp)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                driver TEXT NOT NULL,
                params TEXT NOT NULL DEFAULT '{}',
                location TEXT NOT NULL DEFAULT '',
                enabled INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()
    seed_devices()


DEFAULT_DEVICES = [
    {"name": "inside_climate", "label": "inside climate", "driver": "bme280",
     "params": {"bus": 1, "address": 0x76}, "location": "inside"},
    {"name": "inside_air", "label": "inside air", "driver": "ds18b20",
     "params": {"index": 0}, "location": "inside"},
    {"name": "outside_air", "label": "outside air", "driver": "ds18b20",
     "params": {"index": 1}, "location": "outside"},
    {"name": "circulation", "label": "circulation", "driver": "fan",
     "params": {"pin": 17, "active_low": True, "watch": "inside_air.temperature",
                "on_threshold": 20.0, "off_threshold": 19.0},
     "location": "inside"},
    {"name": "tent_cam", "label": "tent cam", "driver": "camera",
     "params": {"width": 640, "height": 480, "fps": 15}, "location": "inside"},
]


def seed_devices() -> None:
    """Insert default devices if the table is empty."""
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
        if count:
            return
        for d in DEFAULT_DEVICES:
            conn.execute(
                "INSERT INTO devices (name, label, driver, params, location) "
                "VALUES (?, ?, ?, ?, ?)",
                (d["name"], d["label"], d["driver"], json.dumps(d["params"]),
                 d["location"]),
            )
        conn.commit()


def _device_row(row) -> dict:
    d = dict(row)
    d["params"] = json.loads(d["params"])
    d["enabled"] = bool(d["enabled"])
    return d


def get_devices(enabled_only: bool = False) -> list[dict]:
    """All configured devices."""
    query = "SELECT * FROM devices"
    if enabled_only:
        query += " WHERE enabled = 1"
    query += " ORDER BY id"
    with get_db() as conn:
        return [_device_row(r) for r in conn.execute(query).fetchall()]


def get_device(name: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM devices WHERE name = ?", (name,)
        ).fetchone()
        return _device_row(row) if row else None


def upsert_device(d: dict) -> dict:
    """Insert or update a device by name."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO devices (name, label, driver, params, location, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                label=excluded.label, driver=excluded.driver,
                params=excluded.params, location=excluded.location,
                enabled=excluded.enabled
            """,
            (d["name"], d["label"], d["driver"], json.dumps(d.get("params", {})),
             d.get("location", ""), int(d.get("enabled", True))),
        )
        conn.commit()
    return get_device(d["name"])


def delete_device(name: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM devices WHERE name = ?", (name,))
        conn.commit()
        return cur.rowcount > 0


def get_config(key: str, default=None):
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM app_config WHERE key = ?", (key,)
        ).fetchone()
        return json.loads(row["value"]) if row else default


def set_config(key: str, value) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )
        conn.commit()


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(str(settings.database_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def insert_reading(reading: ReadingCreate) -> int:
    """Insert a single reading and return its ID."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO readings (timestamp, sensor, value, unit)
            VALUES (?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(),
                reading.sensor,
                reading.value,
                reading.unit,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def insert_readings_batch(readings: list[ReadingCreate]) -> None:
    """Insert multiple readings in a single transaction."""
    if not readings:
        return
    with get_db() as conn:
        now = datetime.utcnow().isoformat()
        conn.executemany(
            """
            INSERT INTO readings (timestamp, sensor, value, unit)
            VALUES (?, ?, ?, ?)
            """,
            [(now, r.sensor, r.value, r.unit) for r in readings],
        )
        conn.commit()


def get_latest_readings() -> list[dict]:
    """Get the most recent reading for each sensor."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT r.sensor, r.value, r.unit, r.timestamp
            FROM readings r
            INNER JOIN (
                SELECT sensor, MAX(timestamp) as max_ts
                FROM readings
                GROUP BY sensor
            ) latest ON r.sensor = latest.sensor AND r.timestamp = latest.max_ts
            ORDER BY r.sensor
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_history(
    sensor: Optional[str] = None,
    from_time: Optional[datetime] = None,
    to_time: Optional[datetime] = None,
    limit: int = 1000,
) -> list[dict]:
    """Get historical readings with optional filters."""
    query = "SELECT id, timestamp, sensor, value, unit FROM readings WHERE 1=1"
    params: list = []

    if sensor:
        query += " AND sensor = ?"
        params.append(sensor)

    if from_time:
        query += " AND timestamp >= ?"
        params.append(from_time.isoformat())

    if to_time:
        query += " AND timestamp <= ?"
        params.append(to_time.isoformat())

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_stats(from_time: datetime, to_time: Optional[datetime] = None) -> dict:
    """Get min/max for each sensor in a time range."""
    query = """
        SELECT sensor, MIN(value) as min_val, MAX(value) as max_val
        FROM readings
        WHERE timestamp >= ?
    """
    params = [from_time.isoformat()]

    if to_time:
        query += " AND timestamp <= ?"
        params.append(to_time.isoformat())

    query += " GROUP BY sensor"

    with get_db() as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return {
            row["sensor"]: {"min": row["min_val"], "max": row["max_val"]}
            for row in rows
        }


def insert_journal_entry(kind: str, data: dict) -> int:
    """Append an entry to the agent journal. Returns its ID."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO agent_journal (timestamp, kind, data)
            VALUES (?, ?, ?)
            """,
            (datetime.utcnow().isoformat(), kind, json.dumps(data)),
        )
        conn.commit()
        return cursor.lastrowid


def get_journal(limit: int = 50, kind: Optional[str] = None) -> list[dict]:
    """Get journal entries, most recent first. Optionally filter by kind."""
    query = "SELECT id, timestamp, kind, data FROM agent_journal"
    params: list = []
    if kind:
        query += " WHERE kind = ?"
        params.append(kind)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]
