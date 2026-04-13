"""
BME280 and BMP280 I2C temperature, humidity, and pressure sensor driver.
Uses the BME280 combined driver for both sensor types.
"""

import logging
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)

# BME280/BMP280 register map
CHIP_ID = 0x60
BME280_CHIP_ID = 0x60
BMP280_CHIP_ID = 0x58

# Register addresses
REG_CHIP_ID = 0xD0
REG_RESET = 0xE0
REG_CTRL_HUM = 0xF2
REG_STATUS = 0xF3
REG_CTRL_MEAS = 0xF4
REG_CONFIG = 0xF5
REG_DATA = 0xF7


class BME280Reader:
    """Reader for BME280 (temp/humidity/pressure) or BMP280 (temp/pressure) sensors."""

    def __init__(self, bus: int = 1, address: int = 0x76):
        self.bus = bus
        self.address = address
        self._i2c: Optional[object] = None
        self._compensated: bool = False

    def _init_i2c(self) -> None:
        """Initialize I2C connection."""
        try:
            import smbus2

            self._i2c = smbus2.SMBus(self.bus)
            self._compensation_setup()
        except ImportError:
            logger.error("smbus2 not installed. Install with: pip install smbus2")
            raise

    def _compensation_setup(self) -> None:
        """Set up sensor compensation (required after reset)."""
        # Reset
        self._i2c.write_byte_data(self.address, REG_RESET, 0xB6)
        import time

        time.sleep(0.005)  # 5ms startup time

        # Read chip ID to verify
        chip_id = self._i2c.read_byte_data(self.address, REG_CHIP_ID)
        if chip_id not in (BME280_CHIP_ID, BMP280_CHIP_ID):
            logger.warning(
                f"Unexpected chip ID 0x{chip_id:02X} at address 0x{self.address:02X}. "
                f"Expected BME280 (0x{BME280_CHIP_ID:02X}) or BMP280 (0x{BMP280_CHIP_ID:02X})"
            )

        # Set humidity oversampling to 1x
        self._i2c.write_byte_data(self.address, REG_CTRL_HUM, 0x01)

        # Set mode to normal, temp and pressure oversampling to 1x
        self._i2c.write_byte_data(self.address, REG_CTRL_MEAS, 0x27)

        self._compensated = True
        logger.info(f"BME280/BMP280 initialized at 0x{self.address:02X}")

    def _read_calibration(self) -> list:
        """Read calibration coefficients from sensor."""
        calib = []
        try:
            # Read temperature/pressure calibration (24 bytes from 0x88)
            for i in range(0x88, 0x88 + 24):
                calib.append(self._i2c.read_byte_data(self.address, i))
            # Read humidity calibration if BME280 (8 bytes from 0xE1)
            for i in range(0xE1, 0xE1 + 8):
                calib.append(self._i2c.read_byte_data(self.address, i))
            # BME280 has one more byte at 0xE9
            try:
                calib.append(self._i2c.read_byte_data(self.address, 0xE9))
            except Exception:
                pass  # BMP280 doesn't have this
        except Exception as e:
            logger.error(f"Failed to read calibration data: {e}")
            # Return zeros as fallback
            calib = [0] * 33
        return calib

    def _compensation(
        self, raw_temp: int, raw_pressure: int, raw_humidity: int, calib: list
    ) -> tuple[float, float, float]:
        """Apply compensation to raw sensor values."""
        # Temperature compensation (from BME280 datasheet)
        dig_T1 = calib[1] << 8 | calib[0]
        dig_T2 = calib[3] << 8 | calib[2]
        if dig_T2 > 32767:
            dig_T2 -= 65536
        dig_T3 = calib[5] << 8 | calib[4]
        if dig_T3 > 32767:
            dig_T3 -= 65536

        dig_P1 = calib[7] << 8 | calib[6]
        dig_P2 = calib[9] << 8 | calib[8]
        if dig_P2 > 32767:
            dig_P2 -= 65536
        dig_P3 = calib[11] << 8 | calib[10]
        if dig_P3 > 32767:
            dig_P3 -= 65536
        dig_P4 = calib[13] << 8 | calib[12]
        if dig_P4 > 32767:
            dig_P4 -= 65536
        dig_P5 = calib[15] << 8 | calib[14]
        if dig_P5 > 32767:
            dig_P5 -= 65536
        dig_P6 = calib[17] << 8 | calib[16]
        if dig_P6 > 32767:
            dig_P6 -= 65536
        dig_P7 = calib[19] << 8 | calib[18]
        if dig_P7 > 32767:
            dig_P7 -= 65536
        dig_P8 = calib[21] << 8 | calib[20]
        if dig_P8 > 32767:
            dig_P8 -= 65536
        dig_P9 = calib[23] << 8 | calib[22]
        if dig_P9 > 32767:
            dig_P9 -= 65536

        dig_H1 = calib[25]
        dig_H2 = calib[27] << 8 | calib[26]
        if dig_H2 > 32767:
            dig_H2 -= 65536
        dig_H3 = calib[28]
        dig_H4 = calib[29] << 4 | (calib[30] & 0x0F)
        if dig_H4 > 32767:
            dig_H4 -= 65536
        dig_H5 = calib[31] << 4 | (calib[30] >> 4)
        if dig_H5 > 32767:
            dig_H5 -= 65536
        dig_H6 = calib[32]
        if dig_H6 > 127:
            dig_H6 -= 256

        # Temperature
        var1 = (raw_temp / 16384.0 - dig_T1 / 1024.0) * dig_T2
        var2 = ((raw_temp / 131072.0 - dig_T1 / 8192.0) ** 2) * dig_T3
        t_fine = var1 + var2
        temperature = t_fine / 5120.0

        # Pressure
        var1 = t_fine / 2.0 - 64000.0
        var2 = (var1**2) * dig_P6 / 32768.0
        var2 = var2 + var1 * dig_P5 * 2.0
        var2 = var2 / 4.0 + dig_P4 * 65536.0
        var1 = (dig_P3 * var1**2 / 524288.0 + dig_P2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * dig_P1
        if var1 == 0:
            pressure = 0
        else:
            pressure = 1048576.0 - raw_pressure
            pressure = ((pressure - var2 / 4096.0) * 6250.0) / var1
            var1 = dig_P9 * pressure**2 / 2147483648.0
            var2 = pressure * dig_P8 / 32768.0
            pressure = pressure + (var1 + var2 + dig_P7) / 16.0

        # Humidity
        if raw_humidity == 0x8000:
            humidity = 0
        else:
            var1 = t_fine - 76800.0
            var1 = (raw_humidity - (dig_H4 * 64.0 + dig_H5 / 16384.0 * var1)) * (
                dig_H2
                / 65536.0
                * (
                    1.0
                    + dig_H6 / 67108864.0 * var1 * (1.0 + dig_H3 / 67108864.0 * var1)
                )
            )
            var1 = var1 * (1.0 - dig_H1 * var1 / 524288.0)
            humidity = var1
            if humidity < 0:
                humidity = 0
            elif humidity > 100:
                humidity = 100

        return temperature, pressure / 100.0, humidity

    def read(self) -> dict:
        """Read all available values from the sensor.

        Returns dict with temperature (°C), pressure (hPa), and humidity (%) if available.
        """
        if not self._i2c:
            self._init_i2c()

        try:
            # Read raw data
            data = self._i2c.read_i2c_block_data(self.address, REG_DATA, 8)
            raw_pressure = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
            raw_temp = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
            raw_humidity = (data[6] << 8) | data[7]

            calib = self._read_calibration()
            temp, pressure, humidity = self._compensation(
                raw_temp, raw_pressure, raw_humidity, calib
            )

            return {
                "temperature": round(temp, 2),
                "pressure": round(pressure, 2),
                "humidity": round(humidity, 2) if humidity != 0 else None,
            }
        except Exception as e:
            logger.error(f"Error reading BME280/BMP280: {e}")
            return {"temperature": None, "pressure": None, "humidity": None}


class BME280OutsideReader(BME280Reader):
    """BMP280 variant (outside tent, pressure only typically)."""

    pass
