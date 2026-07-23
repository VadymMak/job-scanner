import asyncio

import structlog

from app.config import get_settings
from app.main import pipeline, setup_logging

log = structlog.get_logger("scheduler")


async def run_forever() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    log.info(
        "scheduler started",
        interval_seconds=settings.poll_interval_seconds,
    )

    while True:
        try:
            await pipeline()
        except Exception:
            log.exception("pipeline run failed; continuing")

        log.info(
            "scheduler sleeping",
            seconds=settings.poll_interval_seconds,
        )
        await asyncio.sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(run_forever())
    except KeyboardInterrupt:
        log.info("scheduler stopped by user")
