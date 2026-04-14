"""
API endpoints for current and historical sensor readings.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from ..database import get_history, get_latest_readings, get_stats
from ..models import (
    HistoryQuery,
    Reading,
    SensorReadings,
    SensorStatsResponse,
    PeriodStats,
    SensorStats,
)

router = APIRouter(prefix="/api", tags=["readings"])


def _build_period_stats(stats: dict) -> PeriodStats:
    """Build PeriodStats from raw stats dict."""
    result = PeriodStats()
    if "inside_air_temp" in stats:
        result.inside_air_temp = SensorStats(
            min=stats["inside_air_temp"]["min"], max=stats["inside_air_temp"]["max"]
        )
    if "outside_air_temp" in stats:
        result.outside_air_temp = SensorStats(
            min=stats["outside_air_temp"]["min"], max=stats["outside_air_temp"]["max"]
        )
    if "inside_humidity" in stats:
        result.inside_humidity = SensorStats(
            min=stats["inside_humidity"]["min"], max=stats["inside_humidity"]["max"]
        )
    if "inside_pressure" in stats:
        result.inside_pressure = SensorStats(
            min=stats["inside_pressure"]["min"], max=stats["inside_pressure"]["max"]
        )
    return result


@router.get("/stats", response_model=SensorStatsResponse)
async def get_sensor_stats() -> SensorStatsResponse:
    """Get min/max stats for 24h, 7d, and 30d periods."""
    now = datetime.utcnow()

    day_stats = get_stats(now - timedelta(days=1))
    week_stats = get_stats(now - timedelta(days=7))
    month_stats = get_stats(now - timedelta(days=30))

    # Calculate current temp diff
    readings = get_latest_readings()
    inside_temp = None
    outside_temp = None
    for r in readings:
        if r["sensor"] == "inside_air_temp":
            inside_temp = r["value"]
        elif r["sensor"] == "outside_air_temp":
            outside_temp = r["value"]

    temp_diff = None
    if inside_temp is not None and outside_temp is not None:
        temp_diff = round(inside_temp - outside_temp, 1)

    return SensorStatsResponse(
        day=_build_period_stats(day_stats),
        week=_build_period_stats(week_stats),
        month=_build_period_stats(month_stats),
        temp_diff=temp_diff,
    )


@router.get("/readings", response_model=SensorReadings)
async def get_readings() -> SensorReadings:
    """Get current readings from all sensors (most recent value per sensor)."""
    rows = get_latest_readings()

    result = SensorReadings(timestamp=datetime.utcnow())
    for row in rows:
        sensor = row["sensor"]
        value = row["value"]

        if sensor == "inside_temp":
            result.inside_temp = value
        elif sensor == "inside_humidity":
            result.inside_humidity = value
        elif sensor == "inside_pressure":
            result.inside_pressure = value
        elif sensor == "inside_air_temp":
            result.inside_air_temp = value
        elif sensor == "outside_air_temp":
            result.outside_air_temp = value

    # Try to get timestamp from DB if available
    if rows:
        result.timestamp = datetime.fromisoformat(rows[0]["timestamp"])

    return result


@router.get("/readings/latest", response_model=list[Reading])
async def get_latest() -> list[Reading]:
    """Get the most recent reading for each sensor."""
    rows = get_latest_readings()
    return [
        Reading(
            id=0,  # ID not stored in simplified query
            timestamp=datetime.fromisoformat(row["timestamp"]),
            sensor=row["sensor"],
            value=row["value"],
            unit=row["unit"],
        )
        for row in rows
    ]


@router.get("/history", response_model=list[Reading])
async def get_readings_history(
    sensor: Optional[str] = Query(None, description="Filter by sensor name"),
    from_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    to_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    limit: int = Query(100000, le=200000, description="Max records to return"),
) -> list[Reading]:
    """Get historical sensor readings."""
    rows = get_history(sensor=sensor, from_time=from_time, to_time=to_time, limit=limit)
    return [
        Reading(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            sensor=row["sensor"],
            value=row["value"],
            unit=row["unit"],
        )
        for row in rows
    ]
