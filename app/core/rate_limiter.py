import asyncio
import random
from typing import Optional
from app.config import settings


async def apply_jitter_delay(
    min_seconds: Optional[float] = None,
    max_seconds: Optional[float] = None,
    action_label: str = "navigation",
) -> float:
    """
    Anti-Blocking Jitter: Sleeps for a random interval between min_seconds and max_seconds
    to avoid triggering bot rate-limiting detection during sequential requests.
    """
    min_s = (
        min_seconds
        if min_seconds is not None
        else settings.RATE_LIMIT_MIN_JITTER_SECONDS
    )
    max_s = (
        max_seconds
        if max_seconds is not None
        else settings.RATE_LIMIT_MAX_JITTER_SECONDS
    )

    if min_s > max_s:
        min_s, max_s = max_s, min_s

    sleep_time = random.uniform(min_s, max_s)
    await asyncio.sleep(sleep_time)
    return sleep_time

