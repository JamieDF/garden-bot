from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReadingBase(BaseModel):
    sensor: str
    value: float
    unit: str


class ReadingCreate(ReadingBase):
    pass


class Reading(ReadingBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class SensorReadings(BaseModel):
    """All current readings from all sensors."""

    inside_temp: Optional[float] = None
    inside_humidity: Optional[float] = None
    inside_pressure: Optional[float] = None
    inside_air_temp: Optional[float] = None
    outside_air_temp: Optional[float] = None
    timestamp: datetime


class HistoryQuery(BaseModel):
    sensor: Optional[str] = None
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    limit: int = Field(default=1000, le=10000)
