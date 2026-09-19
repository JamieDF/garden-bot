"""
Fan controller - GPIO relay auto/manual control.
Handles: None temps, corrupted files, inverted thresholds, concurrent access.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Optional

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None  # Not on a Pi (dev machine) - fan control no-ops

logger = logging.getLogger(__name__)

PIN = 17
STATE_FILE = Path.home() / ".garden-bot" / "fan-state.json"
_lock = threading.Lock()
_gpio_initialized = False

DEFAULT_STATE = {
    "state": "off",
    "mode": "manual",
    "on_threshold": 20.0,
    "off_threshold": 19.0,
}


def _ensure_gpio() -> None:
    """Lazy GPIO initialization - only sets up once."""
    global _gpio_initialized
    if GPIO is None:
        return
    if not _gpio_initialized:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PIN, GPIO.OUT, initial=GPIO.HIGH)
        _gpio_initialized = True


def _write(on: bool) -> None:
    """Drive the relay pin (LOW = on). No-op without GPIO."""
    if GPIO is not None:
        GPIO.output(PIN, GPIO.LOW if on else GPIO.HIGH)


def _load() -> dict:
    """Load state. Returns defaults if file missing or corrupted."""
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_STATE.copy()


def _save(data: dict) -> None:
    """Atomic write: temp file + rename, thread-safe."""
    with _lock:
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = STATE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data))
            tmp.rename(STATE_FILE)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")


def get() -> dict:
    """Return current state."""
    return _load()


def set_manual(on: bool) -> dict:
    """Manually turn fan on/off."""
    data = _load()
    data["state"] = "on" if on else "off"
    data["mode"] = "manual"
    _save(data)
    _ensure_gpio()
    _write(on)
    logger.info(f"Manual fan {'ON' if on else 'OFF'}")
    return get()


def set_auto(enabled: bool, on_threshold: float, off_threshold: float) -> dict:
    """Enable/disable auto mode. Raises if thresholds invalid."""
    if enabled and on_threshold <= off_threshold:
        raise ValueError(
            f"on_threshold ({on_threshold}) must be > off_threshold ({off_threshold})"
        )

    data = _load()
    data["mode"] = "auto" if enabled else "manual"
    data["on_threshold"] = on_threshold
    data["off_threshold"] = off_threshold
    _save(data)
    logger.info(
        f"Auto {'enabled' if enabled else 'disabled'}: on>={on_threshold}°C, off<={off_threshold}°C"
    )
    return get()


def check(temp: Optional[float]) -> None:
    """Auto control based on temperature. Safe with None temp."""
    if temp is None:
        return

    data = _load()
    if data["mode"] != "auto":
        return

    is_on = data["state"] == "on"
    on_thr = data["on_threshold"]
    off_thr = data["off_threshold"]

    _ensure_gpio()

    if is_on and temp <= off_thr:
        _write(False)
        data["state"] = "off"
        _save(data)
        logger.info(f"Auto OFF: {temp}°C <= {off_thr}°C")
    elif not is_on and temp >= on_thr:
        _write(True)
        data["state"] = "on"
        _save(data)
        logger.info(f"Auto ON: {temp}°C >= {on_thr}°C")


def init() -> None:
    """Initialize GPIO and restore saved state."""
    _ensure_gpio()
    data = _load()
    _write(data["state"] == "on")
    logger.info(f"Fan init: state={data['state']}, mode={data['mode']}")


def cleanup() -> None:
    if GPIO is not None:
        GPIO.cleanup(PIN)
