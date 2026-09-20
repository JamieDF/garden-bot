"""
Sensor polling service - reads configured sensor devices, writes to DB,
drives relay auto-control on watched sensors.
"""

import logging
import signal
import threading
import time

import httpx

from .config import settings
from .database import init_db, insert_readings_batch
from .models import ReadingCreate
from . import registry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Delta between polls that counts as a notable event, per metric
EVENT_DELTAS = {
    "temperature": 3.0,
    "humidity": 10.0,
    "pressure": 5.0,
    "moisture": 10.0,
}
DEFAULT_DELTA = 5.0


class SensorPoller:
    def __init__(self):
        self.running = True
        self._first_reading = True
        self._prev_values = {}
        self._last_event_wake = 0.0
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        for d in registry.actuator_devices():
            registry.controller_for(d).cleanup()
        self.running = False

    def _init_actuators(self):
        for d in registry.actuator_devices():
            try:
                registry.controller_for(d).init()
            except Exception as e:
                logger.error(f"Error init actuator {d['name']}: {e}")

    def _poll_all(self):
        readings = []
        values = {}  # sensor key -> value, for actuator auto-control
        events = []

        for device in registry.sensor_devices():
            reader = registry.reader_for(device)
            if not reader:
                continue
            try:
                data = reader.read()
            except Exception as e:
                logger.error(f"Error reading {device['name']}: {e}")
                events.append(f"sensor {device['name']} failed to read")
                continue
            for metric, value in data.items():
                if value is None:
                    continue
                if metric == "humidity":
                    value = min(value, 100.0)
                key = f"{device['name']}.{metric}"
                unit = registry.METRIC_UNITS.get(metric, "")
                readings.append(
                    ReadingCreate(sensor=key, value=value, unit=unit)
                )
                values[key] = value

        # Delta events vs previous poll
        for key, value in values.items():
            prev = self._prev_values.get(key)
            if prev is None:
                continue
            metric = key.rsplit(".", 1)[-1]
            if abs(value - prev) >= EVENT_DELTAS.get(metric, DEFAULT_DELTA):
                events.append(f"{key} swung {prev:.1f} -> {value:.1f}")
        self._prev_values = values

        # Relay auto-control on watched sensors
        for device in registry.actuator_devices():
            try:
                ctrl = registry.controller_for(device)
                before = ctrl.get()["state"]
                ctrl.check(values.get(ctrl.watch))
                after = ctrl.get()["state"]
                if before != after:
                    events.append(f"{device['name']} auto {after.upper()}")
            except Exception as e:
                logger.error(f"Error checking {device['name']}: {e}")

        self._maybe_wake_agent(events)
        return readings

    def _maybe_wake_agent(self, events: list[str]):
        """Poke the agent when something notable happened. Debounced."""
        if not events or not settings.llm_enabled:
            return
        now = time.time()
        if now - self._last_event_wake < settings.agent_event_wake_min:
            return
        self._last_event_wake = now
        reason = "; ".join(events)
        logger.info(f"Event wake: {reason}")

        def _poke():
            try:
                httpx.post(
                    f"http://127.0.0.1:{settings.port}/api/agent/wake",
                    json={"reason": reason},
                    timeout=settings.llm_timeout + 30,
                )
            except Exception as e:
                logger.warning(f"Event wake poke failed: {e}")

        threading.Thread(target=_poke, daemon=True).start()

    def run(self):
        logger.info("Sensor poller starting...")
        init_db()
        self._init_actuators()
        logger.info(f"Polling every {settings.poll_interval} seconds")

        while self.running:
            try:
                readings = self._poll_all()
                if readings:
                    if self._first_reading:
                        logger.info("Discarding first reading (warm-up)")
                        self._first_reading = False
                    else:
                        insert_readings_batch(readings)
                else:
                    logger.warning("No readings collected")
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")

            for _ in range(settings.poll_interval):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("Sensor poller stopped")


if __name__ == "__main__":
    SensorPoller().run()
