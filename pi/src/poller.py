"""
Sensor polling service - reads configured sensor devices, writes to DB,
drives relay auto-control on watched sensors.
"""

import logging
import signal
import time

from .config import settings
from .database import init_db, insert_readings_batch
from .models import ReadingCreate
from . import registry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SensorPoller:
    def __init__(self):
        self.running = True
        self._first_reading = True
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

        for device in registry.sensor_devices():
            reader = registry.reader_for(device)
            if not reader:
                continue
            try:
                data = reader.read()
            except Exception as e:
                logger.error(f"Error reading {device['name']}: {e}")
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

        # Relay auto-control on watched sensors
        for device in registry.actuator_devices():
            try:
                ctrl = registry.controller_for(device)
                ctrl.check(values.get(ctrl.watch))
            except Exception as e:
                logger.error(f"Error checking {device['name']}: {e}")

        return readings

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
