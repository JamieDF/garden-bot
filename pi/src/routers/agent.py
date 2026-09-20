"""
Agent status, journal, and manual-wake endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..agent.loop import GardenAgent
from ..config import settings
from ..database import get_journal

router = APIRouter(prefix="/api/agent", tags=["agent"])

_agent = GardenAgent()


@router.get("/status")
async def agent_status() -> dict:
    """Agent configuration and runtime state."""
    return {
        "enabled": settings.llm_enabled,
        "model": settings.llm_model,
        "base_url": settings.llm_base_url,
        "wake_interval": settings.agent_wake_interval,
        "wake_count": _agent.wake_count,
        "last_wake": _agent.last_wake.isoformat() if _agent.last_wake else None,
    }


@router.get("/journal")
async def agent_journal(
    limit: int = Query(50, le=200),
    kind: Optional[str] = Query(None, description="Filter by entry kind"),
) -> list[dict]:
    """Get journal entries, most recent first."""
    return get_journal(limit=limit, kind=kind)


class WakeRequest(BaseModel):
    reason: Optional[str] = None


@router.post("/wake")
async def agent_wake(body: Optional[WakeRequest] = None) -> dict:
    """Trigger a wake cycle manually (for dev/testing)."""
    return await _agent.wake(reason=body.reason if body else None)


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def agent_chat(body: ChatRequest) -> dict:
    """Ask the bot a question - answers with current sensor context."""
    return await _agent.chat(body.message)
