"""
Device registry endpoints - configured sensors and actuators.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import registry
from ..database import delete_device, get_device, get_devices, upsert_device

router = APIRouter(prefix="/api/devices", tags=["devices"])


class DeviceIn(BaseModel):
    name: str
    label: str
    driver: str
    params: dict = {}
    location: str = ""
    enabled: bool = True


class DeviceAction(BaseModel):
    action: str  # "on" | "off" | "auto"
    on_threshold: Optional[float] = None
    off_threshold: Optional[float] = None


@router.get("")
async def list_devices() -> list[dict]:
    """All configured devices."""
    return get_devices()


@router.post("")
async def create_device(body: DeviceIn) -> dict:
    """Create a device (name must be unique)."""
    if get_device(body.name):
        raise HTTPException(400, "device name already exists")
    return upsert_device(body.model_dump())


@router.put("/{name}")
async def update_device(name: str, body: DeviceIn) -> dict:
    """Update a device by name."""
    if not get_device(name):
        raise HTTPException(404, "device not found")
    data = body.model_dump()
    data["name"] = name
    registry.invalidate(name)
    return upsert_device(data)


@router.delete("/{name}")
async def remove_device(name: str) -> dict:
    if not delete_device(name):
        raise HTTPException(404, "device not found")
    registry.invalidate(name)
    return {"deleted": name}


@router.get("/{name}/state")
async def device_state(name: str) -> dict:
    """Current state of a device (actuator state, or sensor latest)."""
    d = get_device(name)
    if not d:
        raise HTTPException(404, "device not found")
    if d["driver"] in registry.ACTUATOR_DRIVERS:
        return registry.controller_for(d).get()
    return d


@router.post("/{name}/action")
async def device_action(name: str, body: DeviceAction) -> dict:
    """Drive an actuator: on, off, or auto (with thresholds)."""
    d = get_device(name)
    if not d or d["driver"] not in registry.ACTUATOR_DRIVERS:
        raise HTTPException(404, "actuator device not found")
    ctrl = registry.controller_for(d)
    if body.action == "on":
        return ctrl.set_manual(True)
    if body.action == "off":
        return ctrl.set_manual(False)
    if body.action == "auto":
        try:
            return ctrl.set_auto(
                True,
                body.on_threshold or 20.0,
                body.off_threshold or 19.0,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
    if body.action == "manual":
        return ctrl.set_auto(
            False,
            body.on_threshold or 20.0,
            body.off_threshold or 19.0,
        )
    raise HTTPException(400, f"unknown action '{body.action}'")
