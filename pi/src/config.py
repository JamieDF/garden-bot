from typing import Optional
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    database_path: Path = Path("/var/lib/garden-bot/readings.db")

    # Polling
    poll_interval: int = 30  # seconds

    # I2C addresses (set bmp280_address to 0 to disable outside sensor)
    bme280_address: int = 0x76  # Inside tent
    bmp280_address: int = 0x77  # Outside tent (0 to disable)

    # 1-Wire device file base
    w1_base: Path = Path("/sys/bus/w1/devices")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_prefix = "GROW_"


settings = Settings()
