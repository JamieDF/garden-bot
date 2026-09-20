"""
Open-Meteo weather fetch - free, no API key.
Used by the agent's observe() so the bot knows the outside world.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather_code -> short description
CONDITIONS = {
    0: "clear sky", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "icy fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "heavy showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm + hail", 99: "thunderstorm + heavy hail",
}


async def fetch(lat: float, lon: float, timeout: float = 8.0) -> Optional[dict]:
    """Current conditions + today's forecast. None on failure."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,is_day",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": 1,
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(URL, params=params)
            r.raise_for_status()
        d = r.json()
        cur = d["current"]
        daily = d.get("daily") or {}
        return {
            "temperature_c": cur["temperature_2m"],
            "humidity_pct": cur["relative_humidity_2m"],
            "wind_kmh": cur["wind_speed_10m"],
            "precip_mm": cur["precipitation"],
            "condition": CONDITIONS.get(cur["weather_code"], f"wmo {cur['weather_code']}"),
            "is_day": bool(cur["is_day"]),
            "today_high_c": (daily.get("temperature_2m_max") or [None])[0],
            "today_low_c": (daily.get("temperature_2m_min") or [None])[0],
            "rain_chance_pct": (daily.get("precipitation_probability_max") or [None])[0],
        }
    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}")
        return None
