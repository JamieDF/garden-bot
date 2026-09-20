"""
Deterministic safety layer - the LLM proposes, these rules dispose.
Every hardware action is validated before it reaches a relay.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .. import registry
from ..database import get_device
from .schemas import Decision

logger = logging.getLogger(__name__)

WATER_COOLDOWN = timedelta(hours=6)  # min time between waterings
WATER_MAX_S = 30.0                   # max pump run per action
WATER_DEFAULT_S = 10.0
MOISTURE_WET_PCT = 60.0              # soil wet enough - don't water

DEVICE_ACTIONS = {"fan_on", "fan_off", "fan_auto", "water"}


@dataclass
class Verdict:
    ok: bool
    reason: Optional[str] = None
    duration_s: Optional[float] = None


def _last_water_ts(entries: list[dict]) -> Optional[datetime]:
    """Most recent executed water action in the journal."""
    for e in entries:
        outcome = e.get("data", {}).get("outcome") or {}
        if outcome.get("executed") == "water":
            try:
                return datetime.fromisoformat(e["timestamp"])
            except (KeyError, ValueError):
                continue
    return None


def _watched_value(device: dict, observation: dict) -> Optional[float]:
    """Current value of the device's watched sensor key, if any."""
    watch = (device.get("params") or {}).get("watch")
    if not watch:
        return None
    for r in observation.get("readings") or []:
        if r.get("sensor") == watch:
            return r.get("value")
    return None


def evaluate(
    decision: Decision, observation: dict, recent: list[dict]
) -> Verdict:
    """Validate a decision's action. Returns ok=False + reason to veto."""
    a = decision.action
    if a not in DEVICE_ACTIONS:
        return Verdict(ok=True)

    dev = get_device(decision.device or "")
    if not dev or dev["driver"] not in registry.ACTUATOR_DRIVERS:
        return Verdict(ok=False, reason=f"unknown actuator '{decision.device}'")

    if a.startswith("fan_"):
        if dev["driver"] != "fan":
            return Verdict(ok=False, reason=f"'{dev['name']}' is not a fan")
        return Verdict(ok=True)

    # a == "water"
    if dev["driver"] != "pump":
        return Verdict(ok=False, reason=f"'{dev['name']}' is not a pump")

    last = _last_water_ts(recent)
    if last and datetime.utcnow() - last < WATER_COOLDOWN:
        return Verdict(
            ok=False,
            reason=f"watered {int((datetime.utcnow() - last).total_seconds() / 60)}min ago "
                   f"(cooldown {WATER_COOLDOWN})",
        )

    wet = _watched_value(dev, observation)
    if wet is not None and wet >= MOISTURE_WET_PCT:
        return Verdict(ok=False, reason=f"soil already wet ({wet:.0f}%)")

    duration = min(decision.duration_s or WATER_DEFAULT_S, WATER_MAX_S)
    return Verdict(ok=True, duration_s=duration)
