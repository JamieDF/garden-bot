"""
Pi Camera 2 MJPEG streaming.
Uses a background thread to read frames, serves them via async generator.
"""

import asyncio
import logging
import subprocess
import threading
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Global state for broadcasting
_frame_queue: asyncio.Queue | None = None
_event_loop: asyncio.AbstractEventLoop | None = None


def _camera_thread():
    """Reads frames from rpicam-vid and puts them in the queue."""
    cmd = [
        "rpicam-vid",
        "--width",
        "640",
        "--height",
        "480",
        "--framerate",
        "15",
        "--codec",
        "mjpeg",
        "--output",
        "-",
        "--nopreview",
        "-t",
        "0",
    ]

    logger.info("Camera thread starting: %s", " ".join(cmd))

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )

    buf = bytearray()
    SOI = bytes([0xFF, 0xD8])
    EOI = bytes([0xFF, 0xD9])
    frame_count = 0

    try:
        while True:
            chunk = proc.stdout.read(32768)
            if not chunk:
                logger.warning("Camera EOF")
                break
            buf.extend(chunk)

            while True:
                start = buf.find(SOI)
                if start == -1:
                    buf = buf[-1:]
                    break
                end = buf.find(EOI, start + 2)
                if end == -1:
                    if start > 0:
                        del buf[:start]
                    break
                frame = bytes(buf[start : end + 2])
                del buf[: end + 2]
                frame_count += 1

                # Put frame in queue
                if _frame_queue and _event_loop:
                    try:
                        _event_loop.call_soon_threadsafe(
                            lambda f: (
                                _frame_queue.put_nowait(f)
                                if not _frame_queue.full()
                                else None
                            ),
                            frame,
                        )
                    except Exception:
                        pass
    finally:
        proc.terminate()
        proc.wait()
        logger.info("Camera thread stopped, %d frames sent", frame_count)


async def get_jpeg_frames() -> AsyncGenerator[bytes, None]:
    """Async generator that yields frames from the camera thread."""
    global _frame_queue, _event_loop

    _frame_queue = asyncio.Queue(maxsize=2)
    _event_loop = asyncio.get_running_loop()

    # Start camera thread
    t = threading.Thread(target=_camera_thread, daemon=True, name="camera")
    t.start()
    logger.info("Camera thread started")

    try:
        while True:
            try:
                frame = await asyncio.wait_for(_frame_queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
    finally:
        _frame_queue = None
        _event_loop = None
        logger.info("Client disconnected")
