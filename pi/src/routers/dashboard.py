"""
Dashboard layout endpoints - widget canvas persisted server-side.
Layout is a list of {i, type, x, y, w, h, config} on a 12-col grid.
"""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..database import get_config, set_config

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

DEFAULT_LAYOUT = [
    {"i": "bot", "type": "bot", "x": 0, "y": 0, "w": 8, "h": 4, "minH": 4,
     "config": {}},
    {"i": "cam", "type": "camera", "x": 8, "y": 0, "w": 4, "h": 4,
     "config": {"device": "tent_cam"}},
    {"i": "m1", "type": "metric", "x": 0, "y": 4, "w": 3, "h": 1,
     "config": {"sensor": "inside_air.temperature"}},
    {"i": "m2", "type": "metric", "x": 3, "y": 4, "w": 3, "h": 1,
     "config": {"sensor": "outside_air.temperature"}},
    {"i": "m3", "type": "metric", "x": 6, "y": 4, "w": 3, "h": 1,
     "config": {"sensor": "inside_climate.humidity"}},
    {"i": "m4", "type": "metric", "x": 9, "y": 4, "w": 3, "h": 1,
     "config": {"sensor": "inside_climate.pressure"}},
    {"i": "chart", "type": "chart", "x": 0, "y": 5, "w": 8, "h": 4,
     "config": {}},
    {"i": "fan", "type": "fan", "x": 8, "y": 5, "w": 4, "h": 4,
     "config": {"device": "circulation"}},
    {"i": "journal", "type": "journal", "x": 0, "y": 9, "w": 12, "h": 3,
     "config": {}},
]


class LayoutItem(BaseModel):
    i: str
    type: str
    x: int
    y: int
    w: int
    h: int
    minW: Optional[int] = None
    minH: Optional[int] = None
    config: dict = {}


@router.get("/layout")
async def get_layout() -> list[dict]:
    """Current dashboard widget layout."""
    return get_config("dashboard_layout", DEFAULT_LAYOUT)


@router.put("/layout")
async def put_layout(body: list[LayoutItem]) -> list[dict]:
    """Save dashboard widget layout."""
    items = [item.model_dump() for item in body]
    set_config("dashboard_layout", items)
    return items
