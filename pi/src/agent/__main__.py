"""
Scheduled agent daemon: python -m src.agent
Wakes every GROW_AGENT_WAKE_INTERVAL seconds and runs the wake cycle.
"""

import asyncio
import logging
import signal

from ..config import settings
from .loop import GardenAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    agent = GardenAgent()
    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    if not settings.llm_enabled:
        logger.warning("GROW_LLM_ENABLED is false - wakes will be no-ops")
    logger.info(
        f"Garden agent started, waking every {settings.agent_wake_interval}s "
        f"(model={settings.llm_model} @ {settings.llm_base_url})"
    )

    while not stop.is_set():
        result = await agent.wake()
        if result["status"] != "disabled":
            logger.info(f"Wake result: {result['status']}")
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.agent_wake_interval)
        except asyncio.TimeoutError:
            pass

    logger.info("Garden agent stopped")


if __name__ == "__main__":
    asyncio.run(main())
