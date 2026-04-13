"""
MJPEG video streaming endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..camera.stream import get_jpeg_frames

router = APIRouter(tags=["stream"])


@router.get("/stream.mjpg")
async def stream_video() -> StreamingResponse:
    """Stream live video from Pi Camera as MJPEG."""
    return StreamingResponse(
        get_jpeg_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
