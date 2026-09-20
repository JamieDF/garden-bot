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

    # Agent / LLM (any OpenAI-compatible endpoint: llama-server, Ollama, hosted)
    llm_enabled: bool = False
    llm_base_url: str = "http://localhost:8080/v1"
    llm_model: str = "smollm2-135m"
    llm_api_key: str = "none"
    llm_timeout: float = 60.0
    agent_wake_interval: int = 1800  # seconds between wakes
    agent_journal_recall: int = 5  # past decisions fed back as memory

    # Weather (Open-Meteo, no key needed). Agent observes weather only
    # when both are set.
    weather_lat: Optional[float] = None
    weather_lon: Optional[float] = None

    class Config:
        env_prefix = "GROW_"


settings = Settings()
