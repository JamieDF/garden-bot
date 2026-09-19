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

from ..config import settings
from ..database import (
    get_journal,
    get_latest_readings,
    get_stats,
    insert_journal_entry,
)
from ..sensors import fan
from .llm import LLMClient
from .schemas import Decision

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Garden Bot, a small robot tending plants.
You wake up, look at your sensor readings, and say one short sentence.
Be charming and a little odd. Max 20 words for "speak".
You cannot act yet - you only observe and speak."""


class GardenAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.last_wake: Optional[datetime] = None
        self.wake_count = 0

    def observe(self) -> dict:
        """Snapshot the world: sensors, 24h stats, fan state."""
        return {
            "readings": get_latest_readings(),
            "stats_24h": get_stats(datetime.utcnow() - timedelta(days=1)),
            "fan": fan.get(),
            "time": datetime.utcnow().isoformat(),
        }

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
            observation = self.observe()
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
            logger.error(f"Wake failed: {e}")
            insert_journal_entry("error", {"error": str(e)})
            return {"status": "error", "error": str(e)}
