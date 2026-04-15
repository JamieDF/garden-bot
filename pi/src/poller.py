"""
Sensor polling service - reads sensors, writes to DB, controls fan.
"""

import logging
import signal
import time

from .config import settings
from .database import init_db, insert_readings_batch
from .models import ReadingCreate
from .sensors import BME280Reader, create_probe_readers
from .sensors import fan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SensorPoller:
    def __init__(self):
        self.running = True
        self.sensors = {}
        self._first_reading = True
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        fan.cleanup()
        self.running = False

    def _init_sensors(self):
        logger.info("Initializing sensors...")
        self.sensors["inside"] = BME280Reader(bus=1, address=settings.bme280_address)
        self.sensors["ds18b20"] = create_probe_readers()
        logger.info(f"Initialized sensors: {list(self.sensors.keys())}")

    def _poll_all(self):
        readings = []
        inside_air_temp = None

        # BME280
        try:
            data = self.sensors["inside"].read()
            if data["temperature"] is not None:
                readings.append(
                    ReadingCreate(
                        sensor="inside_temp", value=data["temperature"], unit="°C"
                    )
                )
            if data["humidity"] is not None:
                readings.append(
                    ReadingCreate(
                        sensor="inside_humidity",
                        value=min(data["humidity"], 100.0),
                        unit="%",
                    )
                )
            if data["pressure"] is not None:
                readings.append(
                    ReadingCreate(
                        sensor="inside_pressure", value=data["pressure"], unit="hPa"
                    )
                )
        except Exception as e:
            logger.error(f"Error reading BME280: {e}")

        # DS18B20 probes
        ds18b20 = self.sensors.get("ds18b20", {})
        for probe_name, reader in ds18b20.items():
            try:
                data = reader.read()
                if data["temperature"] is not None:
                    readings.append(
                        ReadingCreate(
                            sensor=f"{probe_name}_temp",
                            value=data["temperature"],
                            unit="°C",
                        )
                    )
                    if probe_name == "inside_air":
                        inside_air_temp = data["temperature"]
            except Exception as e:
                logger.error(f"Error reading {probe_name}: {e}")

        # Fan auto control
        fan.check(inside_air_temp)

        return readings

    def run(self):
        logger.info("Sensor poller starting...")
        init_db()
        self._init_sensors()
        fan.init()
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
