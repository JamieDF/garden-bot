"""
Sensor polling service - runs as a daemon or systemd service.
Reads all sensors and writes to the database.
"""

import logging
import signal
import sys
import time
from pathlib import Path

from .config import settings
from .database import init_db, insert_readings_batch
from .models import ReadingCreate
from .sensors import BME280Reader, create_probe_readers, DS18B20Reader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SensorPoller:
    """Polls all sensors and writes readings to the database."""

    def __init__(self):
        self.running = True
        self.sensors: dict = {}
        self._first_reading = True  # Discard first reading (often garbage)

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def _init_sensors(self) -> None:
        """Initialize all sensor readers."""
        logger.info("Initializing sensors...")

        # BME280 - Inside tent (temperature, humidity, pressure)
        self.sensors["inside"] = BME280Reader(
            bus=1,
            address=settings.bme280_address,
        )

        # DS18B20 probes (1-wire)
        self.sensors["ds18b20"] = create_probe_readers()

        logger.info(f"Initialized sensors: {list(self.sensors.keys())}")

    def _poll_all(self) -> list[ReadingCreate]:
        """Poll all sensors and return readings."""
        readings: list[ReadingCreate] = []

        # BME280 Inside
        try:
            data = self.sensors["inside"].read()
            logger.info(f"Inside sensor data: {data}")
            if data["temperature"] is not None:
                readings.append(
                    ReadingCreate(
                        sensor="inside_temp",
                        value=data["temperature"],
                        unit="°C",
                    )
                )
            if data["humidity"] is not None:
                # Cap humidity at 100% (sensor can occasionally read slightly over)
                humidity = min(data["humidity"], 100.0)
                readings.append(
                    ReadingCreate(
                        sensor="inside_humidity",
                        value=humidity,
                        unit="%",
                    )
                )
            if data["pressure"] is not None:
                readings.append(
                    ReadingCreate(
                        sensor="inside_pressure",
                        value=data["pressure"],
                        unit="hPa",
                    )
                )
        except Exception as e:
            logger.error(f"Error reading inside sensor: {e}")

        # DS18B20 probes (inside air and outside air)
        ds18b20_readers = self.sensors.get("ds18b20", {})
        for probe_name, reader in ds18b20_readers.items():
            try:
                data = reader.read()
                if data["temperature"] is not None:
                    logger.info(f"{probe_name} reading: {data['temperature']}°C")
                    sensor_name = f"{probe_name}_temp"
                    readings.append(
                        ReadingCreate(
                            sensor=sensor_name,
                            value=data["temperature"],
                            unit="°C",
                        )
                    )
            except Exception as e:
                logger.error(f"Error reading {probe_name} probe: {e}")

        return readings

    def run(self) -> None:
        """Main polling loop."""
        logger.info("Sensor poller starting...")

        # Ensure database is initialized
        init_db()

        # Initialize sensors
        self._init_sensors()

        logger.info(f"Polling every {settings.poll_interval} seconds")

        while self.running:
            try:
                readings = self._poll_all()
                if readings:
                    if self._first_reading:
                        logger.info("Discarding first reading (sensor warm-up)")
                        self._first_reading = False
                    else:
                        insert_readings_batch(readings)
                        logger.debug(f"Wrote {len(readings)} readings")
                else:
                    logger.warning("No readings collected")
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")

            # Sleep in small increments to allow fast shutdown
            for _ in range(settings.poll_interval):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("Sensor poller stopped")


def main():
    """Entry point."""
    poller = SensorPoller()
    poller.run()


if __name__ == "__main__":
    main()
