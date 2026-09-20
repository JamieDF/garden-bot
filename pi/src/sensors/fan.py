"""
Relay controller - GPIO relay auto/manual control, per configured device.
Handles fans and pumps: None temps, corrupted files, inverted thresholds.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Optional

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None  # Not on a Pi (dev machine) - output control no-ops

logger = logging.getLogger(__name__)

STATE_DIR = Path.home() / ".garden-bot" / "relays"
_lock = threading.Lock()


class FanController:
    """A single relay-driven actuator with optional auto thresholds."""

    def __init__(
        self,
        name: str,
        pin: int = 17,
        active_low: bool = True,
        watch: str = "",
        on_threshold: float = 20.0,
        off_threshold: float = 19.0,
    ):
        self.name = name
        self.pin = pin
        self.active_low = active_low
        self.watch = watch  # sensor key this device auto-controls on
        self.defaults = {
            "state": "off",
            "mode": "manual",
            "on_threshold": on_threshold,
            "off_threshold": off_threshold,
        }
        self.state_file = STATE_DIR / f"{name}.json"
        self._gpio_ready = False

    @classmethod
    def from_device(cls, device: dict) -> "FanController":
        p = device["params"]
        return cls(
            name=device["name"],
            pin=p.get("pin", 17),
            active_low=p.get("active_low", True),
            watch=p.get("watch", ""),
            on_threshold=p.get("on_threshold", 20.0),
            off_threshold=p.get("off_threshold", 19.0),
        )

    def _ensure_gpio(self) -> None:
        """Lazy GPIO initialization - only sets up once."""
        if GPIO is None or self._gpio_ready:
            return
        GPIO.setmode(GPIO.BCM)
        # Relay rests in the "off" level
        off_level = GPIO.LOW if self.active_low else GPIO.HIGH
        GPIO.setup(self.pin, GPIO.OUT, initial=off_level)
        self._gpio_ready = True

    def _write(self, on: bool) -> None:
        """Drive the relay pin. No-op without GPIO."""
        if GPIO is None:
            return
        on_level = GPIO.LOW if self.active_low else GPIO.HIGH
        off_level = GPIO.HIGH if self.active_low else GPIO.LOW
        GPIO.output(self.pin, on_level if on else off_level)

    def _load(self) -> dict:
        """Load state. Returns defaults if file missing or corrupted."""
        try:
            with open(self.state_file) as f:
                return {**self.defaults, **json.load(f)}
        except (FileNotFoundError, json.JSONDecodeError):
            return self.defaults.copy()

    def _save(self, data: dict) -> None:
        """Atomic write: temp file + rename, thread-safe."""
        with _lock:
            try:
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.state_file.with_suffix(".tmp")
                tmp.write_text(json.dumps(data))
                tmp.rename(self.state_file)
            except Exception as e:
                logger.error(f"Failed to save state: {e}")

    def get(self) -> dict:
        """Return current state."""
        data = self._load()
        data.update({"name": self.name, "pin": self.pin, "watch": self.watch})
        return data

    def set_manual(self, on: bool) -> dict:
        """Manually turn the relay on/off."""
        data = self._load()
        data["state"] = "on" if on else "off"
        data["mode"] = "manual"
        self._save(data)
        self._ensure_gpio()
        self._write(on)
        logger.info(f"[{self.name}] manual {'ON' if on else 'OFF'}")
        return self.get()

    def set_auto(
        self, enabled: bool, on_threshold: float, off_threshold: float
    ) -> dict:
        """Enable/disable auto mode. Raises if thresholds invalid."""
        if enabled and on_threshold <= off_threshold:
            raise ValueError(
                f"on_threshold ({on_threshold}) must be > off_threshold ({off_threshold})"
            )
        data = self._load()
        data["mode"] = "auto" if enabled else "manual"
        data["on_threshold"] = on_threshold
        data["off_threshold"] = off_threshold
        self._save(data)
        logger.info(
            f"[{self.name}] auto {'enabled' if enabled else 'disabled'}: "
            f"on>={on_threshold}°C, off<={off_threshold}°C"
        )
        return self.get()

    def check(self, temp: Optional[float]) -> None:
        """Auto control based on temperature. Safe with None temp."""
        if temp is None:
            return
        data = self._load()
        if data["mode"] != "auto":
            return

        is_on = data["state"] == "on"
        on_thr = data["on_threshold"]
        off_thr = data["off_threshold"]

        self._ensure_gpio()

        if is_on and temp <= off_thr:
            self._write(False)
            data["state"] = "off"
            self._save(data)
            logger.info(f"[{self.name}] auto OFF: {temp}°C <= {off_thr}°C")
        elif not is_on and temp >= on_thr:
            self._write(True)
            data["state"] = "on"
            self._save(data)
            logger.info(f"[{self.name}] auto ON: {temp}°C >= {on_thr}°C")

    def init(self) -> None:
        """Initialize GPIO and restore saved state."""
        self._ensure_gpio()
        self._write(self._load()["state"] == "on")
        data = self._load()
        logger.info(
            f"[{self.name}] init: state={data['state']}, mode={data['mode']}"
        )

    def cleanup(self) -> None:
        if GPIO is not None and self._gpio_ready:
            GPIO.cleanup(self.pin)
            self._gpio_ready = False
