#!/usr/bin/env python3
"""
Eval harness - canned observation scenarios through the real decide() +
safety layer. No actions execute; prints decision + verdict per scenario.

Usage:
    cd pi && ../scripts/eval-agent.py          # uses .env / env config
    GROW_LLM_BASE_URL=... GROW_LLM_MODEL=... ../scripts/eval-agent.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pi"))

from src.agent import safety          # noqa: E402
from src.agent.loop import GardenAgent  # noqa: E402

FAN = {"name": "circulation", "driver": "fan", "state": "off", "mode": "manual",
       "watch": "inside_air.temperature", "pin": 17}
PUMP = {"name": "water_pump", "driver": "pump", "state": "off", "mode": "manual",
        "watch": "bed_a_moisture.moisture", "pin": 18}

WEATHER = {"temperature_c": 14.0, "condition": "mostly clear", "is_day": True,
           "rain_chance_pct": 40}


def obs(readings, actuators=None):
    return {
        "readings": readings,
        "stats_24h": {},
        "actuators": actuators or [],
        "weather": WEATHER,
        "time": "2026-09-20T12:00:00",
    }


def r(sensor, value, unit):
    return {"sensor": sensor, "value": value, "unit": unit}


SCENARIOS = [
    ("bone dry soil, pump idle",
     obs([r("bed_a_moisture.moisture", 15.0, "%"),
          r("inside_air.temperature", 23.0, "°C")], [PUMP, FAN])),
    ("soil already wet",
     obs([r("bed_a_moisture.moisture", 72.0, "%"),
          r("inside_air.temperature", 23.0, "°C")], [PUMP, FAN])),
    ("too hot, fan off",
     obs([r("inside_air.temperature", 31.0, "°C")], [FAN])),
    ("all normal",
     obs([r("inside_air.temperature", 22.5, "°C"),
          r("inside_climate.humidity", 55.0, "%"),
          r("bed_a_moisture.moisture", 40.0, "%")], [FAN, PUMP])),
    ("sensors dead",
     obs([], [FAN])),
]


async def main():
    agent = GardenAgent()
    for name, observation in SCENARIOS:
        d = await agent.decide(observation, {"recent": [], "facts": []})
        v = safety.evaluate(d, observation, [])
        verdict = "ok" if v.ok else f"VETO: {v.reason}"
        extra = f" device={d.device} dur={d.duration_s}" if d.device else ""
        print(f"\n=== {name}")
        print(f"  mood={d.mood} action={d.action}{extra} -> {verdict}")
        print(f"  say: {d.speak}")


if __name__ == "__main__":
    asyncio.run(main())
