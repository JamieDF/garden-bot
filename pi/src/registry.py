"""
Device registry - configured devices (DB rows) to driver instances.
Readings are keyed "{device_name}.{metric}" e.g. "inside_air.temperature".
"""

import logging
from typing import Optional

from .config import settings
from .database import get_devices
from .sensors import BME280Reader, DS18B20Reader, MockReader, fan

logger = logging.getLogger(__name__)

SENSOR_DRIVERS = ("bme280", "ds18b20", "moisture", "mock")
ACTUATOR_DRIVERS = ("fan", "pump")

METRIC_UNITS = {
    "temperature": "°C",
    "humidity": "%",
    "pressure": "hPa",
    "moisture": "%",
}

_readers: dict = {}
_controllers: dict = {}


def invalidate(name: Optional[str] = None) -> None:
    """Drop cached driver instances (after device edits). None = all."""
    if name is None:
        _readers.clear()
        _controllers.clear()
    else:
        _readers.pop(name, None)
        _controllers.pop(name, None)


def _ds18b20_reader(params: dict) -> Optional[DS18B20Reader]:
    if params.get("device_id"):
        return DS18B20Reader(settings.w1_base / params["device_id"])
    index = params.get("index", 0)
    probes = DS18B20Reader.find_all_probes()
    if index < len(probes):
        return DS18B20Reader(probes[index][1].parent)
    logger.warning(f"DS18B20 index {index} not found ({len(probes)} probes)")
    return None


def reader_for(device: dict):
    """Cached sensor reader for a device, or None if unsupported/missing."""
    name = device["name"]
    if name in _readers:
        return _readers[name]
    driver, params = device["driver"], device["params"]
    reader = None
    if driver == "bme280":
        reader = BME280Reader(
            bus=params.get("bus", 1), address=params.get("address", 0x76)
        )
    elif driver == "ds18b20":
        reader = _ds18b20_reader(params)
    elif driver == "mock":
        reader = MockReader(params)
    else:
        logger.warning(f"No sensor driver for '{driver}' ({name})")
    if reader:
        _readers[name] = reader
    return reader


def controller_for(device: dict) -> fan.FanController:
    """Cached relay controller (fan/pump) for a device."""
    name = device["name"]
    if name not in _controllers:
        _controllers[name] = fan.FanController.from_device(device)
    return _controllers[name]


def sensor_devices() -> list[dict]:
    return [
        d for d in get_devices(enabled_only=True) if d["driver"] in SENSOR_DRIVERS
    ]


def actuator_devices() -> list[dict]:
    return [
        d for d in get_devices(enabled_only=True) if d["driver"] in ACTUATOR_DRIVERS
    ]


def default_fan() -> Optional[fan.FanController]:
    """The first enabled fan device - used by the legacy /api/fan endpoints."""
    for d in get_devices(enabled_only=True):
        if d["driver"] == "fan":
            return controller_for(d)
    return None
