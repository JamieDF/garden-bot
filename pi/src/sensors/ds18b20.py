"""
DS18B20 1-Wire temperature sensor driver.
Reads temperature from DS18B20 probes on the 1-Wire bus.
"""

import logging
from pathlib import Path
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)


class DS18B20Reader:
    """Reader for DS18B20 1-Wire temperature probes."""

    def __init__(self, device_path: Optional[Path] = None):
        self.device_path = device_path
        self._device_file: Optional[Path] = None

    def _find_device_file(self) -> Optional[Path]:
        """Find the w1_slave file for this device."""
        if self.device_path:
            w1_slave = self.device_path / "w1_slave"
            if w1_slave.exists():
                return w1_slave

        # If no specific path, this is handled by finding devices by ID
        return None

    def _read_temperature(self, device_path: Path) -> Optional[float]:
        """Read temperature from a w1_slave file."""
        try:
            with open(device_path, "r") as f:
                lines = f.readlines()

            # Check for valid reading
            if lines[0].strip()[-3:] != "YES":
                logger.warning(f"CRC check failed for {device_path}")
                return None

            # Find temperature value (t=xxxxx format)
            for line in lines:
                if "t=" in line:
                    temp_str = line.split("t=")[1].strip()
                    # DS18B20 outputs in 1/1000 degrees
                    temp_celsius = int(temp_str) / 1000.0
                    return round(temp_celsius, 2)

            logger.warning(f"No temperature value found in {device_path}")
            return None

        except FileNotFoundError:
            logger.error(f"Device file not found: {device_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading {device_path}: {e}")
            return None

    def read(self) -> dict:
        """Read temperature from this probe.

        Returns dict with 'temperature' key (°C) or None if reading failed.
        """
        if not self._device_file:
            self._device_file = self._find_device_file()

        if self._device_file:
            temp = self._read_temperature(self._device_file)
            return {"temperature": temp}
        else:
            return {"temperature": None}

    @staticmethod
    def find_all_probes(w1_base: Optional[Path] = None) -> list[tuple[str, Path]]:
        """Find all DS18B20 devices on the 1-Wire bus.

        Returns list of (device_id, device_path) tuples.
        """
        if w1_base is None:
            w1_base = settings.w1_base

        if not w1_base.exists():
            logger.error(f"1-Wire bus not found at {w1_base}")
            return []

        devices = []
        try:
            for entry in w1_base.iterdir():
                # DS18B20 devices have directories starting with "28-"
                if entry.is_dir() and entry.name.startswith("28-"):
                    w1_slave = entry / "w1_slave"
                    if w1_slave.exists():
                        devices.append((entry.name, w1_slave))
        except PermissionError:
            logger.error(f"Permission denied accessing {w1_base}")
            return []

        logger.info(f"Found {len(devices)} DS18B20 probe(s)")
        return sorted(devices, key=lambda x: x[0])


def create_probe_readers() -> dict[str, DS18B20Reader]:
    """Create readers for all detected DS18B20 probes.

    Returns dict mapping probe names ('air', 'soil', or 'probe_N') to readers.
    """
    probes = DS18B20Reader.find_all_probes()
    readers = {}

    if len(probes) == 0:
        logger.warning("No DS18B20 probes found")
    elif len(probes) == 1:
        # Single probe - use as air probe
        readers["air"] = DS18B20Reader(probes[0][1].parent)
        logger.info("Single probe assigned as 'air_probe'")
    elif len(probes) == 2:
        # Two probes - first is inside air, second is outside air
        readers["inside_air"] = DS18B20Reader(probes[0][1].parent)
        readers["outside_air"] = DS18B20Reader(probes[1][1].parent)
        logger.info("Two probes assigned as 'inside_air' and 'outside_air'")
    else:
        # Multiple probes - assign numbered names
        logger.warning(
            f"More than 2 probes found ({len(probes)}). Assigning generic names."
        )
        for i, (dev_id, path) in enumerate(probes):
            readers[f"probe_{i}"] = DS18B20Reader(path.parent)

    return readers
