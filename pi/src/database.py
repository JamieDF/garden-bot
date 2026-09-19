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
