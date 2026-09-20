"""
Fan control API endpoints - operate on the default fan device.
(Device-agnostic control lives at POST /api/devices/{name}/action.)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import registry

router = APIRouter(prefix="/api", tags=["fan"])


class FanManualRequest(BaseModel):
    on: bool


class FanAutoRequest(BaseModel):
    enabled: bool
    on_threshold: float = 20.0
    off_threshold: float = 19.0


def _fan():
    ctrl = registry.default_fan()
    if not ctrl:
        raise HTTPException(404, "no fan device configured")
    return ctrl


@router.get("/fan")
async def get_fan_state():
    """Get current fan state, mode, and thresholds."""
    return _fan().get()


@router.post("/fan")
async def set_fan_state(body: FanManualRequest):
    """Manually turn fan on or off."""
    return _fan().set_manual(body.on)


@router.put("/fan/auto")
async def set_auto_mode(body: FanAutoRequest):
    """Set auto mode with temperature thresholds."""
    if body.on_threshold <= body.off_threshold:
        raise HTTPException(400, "on_threshold must be > off_threshold")
    return _fan().set_auto(body.enabled, body.on_threshold, body.off_threshold)
