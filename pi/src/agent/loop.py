"""
The agent wake cycle: observe -> recall -> decide -> act -> journal.

Phase 0/1: narration only. The action whitelist admits "none"/"speak";
fan control stays with the deterministic auto mode in sensors/fan.py.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from pydantic import ValidationError

from .. import registry, weather
from ..config import settings
from ..database import (
    get_journal,
    get_latest_readings,
    get_stats,
    insert_journal_entry,
)
from .llm import LLMClient
from .schemas import Decision

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Garden Bot, a small robot tending plants.
You wake up, look at your sensor readings, and say one short sentence.
Be charming and a little odd. Max 20 words for "speak".
You cannot act yet - you only observe and speak."""

CHAT_SYSTEM = """You are Garden Bot, a small robot tending plants.
You answer questions about the garden using the sensor context given.
Be charming and a little odd. Keep answers to one or two short sentences."""


class GardenAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.last_wake: Optional[datetime] = None
        self.wake_count = 0

    def observe(self) -> dict:
        """Snapshot the world: sensors, 24h stats, fan state."""
        fan_dev = registry.default_fan()
        return {
            "readings": get_latest_readings(),
            "stats_24h": get_stats(datetime.utcnow() - timedelta(days=1)),
            "fan": fan_dev.get() if fan_dev else None,
            "time": datetime.utcnow().isoformat(),
        }

    async def _observe(self) -> dict:
        """observe() + outside weather when configured."""
        obs = self.observe()
        if settings.weather_lat is not None and settings.weather_lon is not None:
            obs["weather"] = await weather.fetch(
                settings.weather_lat, settings.weather_lon
            )
        return obs

    def recall(self) -> list[dict]:
        """Recent decisions = the bot's short-term memory."""
        return get_journal(limit=settings.agent_journal_recall, kind="decision")

    async def decide(self, observation: dict, memory: list[dict]) -> Decision:
        """Prompt the model for a structured decision."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"observation": observation, "recent_memory": memory}
                ),
            },
        ]
        raw = await self.llm.chat(
            messages, json_schema=Decision.model_json_schema()
        )
        try:
            return Decision.model_validate_json(raw)
        except ValidationError as e:
            logger.warning(f"Unparseable decision: {e}; raw={raw!r}")
            return Decision(
                mood="confused", observation="unparseable thoughts", action="none"
            )

    def act(self, decision: Decision) -> dict:
        """Execute whitelisted actions. Phase 0: narration only."""
        if decision.action == "speak" and decision.speak:
            return {"narration": decision.speak}
        return {}

    async def wake(self) -> dict:
        """One full wake cycle. Returns a result summary."""
        if not settings.llm_enabled:
            return {"status": "disabled"}

        self.wake_count += 1
        self.last_wake = datetime.utcnow()

        try:
            observation = await self._observe()
            memory = self.recall()
            decision = await self.decide(observation, memory)
            outcome = self.act(decision)
            insert_journal_entry(
                "decision",
                {
                    "observation": observation,
                    "memory_used": len(memory),
                    "decision": decision.model_dump(),
                    "outcome": outcome,
                },
            )
            return {
                "status": "ok",
                "decision": decision.model_dump(),
                "outcome": outcome,
            }
        except Exception as e:
            logger.exception("Wake failed")
            insert_journal_entry("error", {"error": repr(e)})
            return {"status": "error", "error": repr(e)}

    async def chat(self, message: str) -> dict:
        """Free-form question -> in-character answer with sensor context."""
        if not settings.llm_enabled:
            return {"status": "disabled", "reply": "zZz — brain not plugged in."}

        observation = await self._observe()
        memory = self.recall()
        past = list(reversed(get_journal(limit=8, kind="chat")))
        turns = []
        for e in past:
            turns.append({"role": "user", "content": e["data"]["user"]})
            turns.append({"role": "assistant", "content": e["data"]["bot"]})

        messages = [
            {"role": "system", "content": CHAT_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "sensor_context": observation,
                        "recent_memory": memory,
                    }
                ),
            },
            *turns,
            {"role": "user", "content": message},
        ]
        reply = await self.llm.chat(messages, max_tokens=160)
        insert_journal_entry("chat", {"user": message, "bot": reply})
        return {"status": "ok", "reply": reply}
