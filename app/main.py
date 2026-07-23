import asyncio
import logging

import structlog
from sqlalchemy import func, update

from app.config import get_settings
from app.core.pipeline import ingest
from app.db.models import Run
from app.db.session import AsyncSessionLocal
from app.notify.telegram import notify_scored
from app.relevance.embeddings import embed_pending_jobs
from app.relevance.hybrid import rank_candidates
from app.relevance.llm_judge import score_top_candidates
from app.relevance.prefilter import prefilter_new_jobs
from app.sources.remoteok import RemoteOKSource

log = structlog.get_logger("pipeline")


def setup_logging(level: str) -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))


async def pipeline() -> None:
    """Один полный прогон с записью старта/финиша в таблицу runs."""

    # --- Открываем запись прогона ---
    async with AsyncSessionLocal() as session:
        run = Run()
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    fetched = new = notified = 0
    error: str | None = None

    try:
        r = await ingest(RemoteOKSource())
        fetched = r["fetched"]
        new = r["new"]

        await prefilter_new_jobs()
        await embed_pending_jobs()

        top = await rank_candidates()
        await score_top_candidates(top)

        n = await notify_scored()
        notified = n["sent"]

    except Exception as e:
        error = repr(e)
        log.exception("pipeline failed", run_id=run_id)
        raise

    finally:
        # Новая сессия — чистая даже если пайплайн упал внутри транзакции
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(Run)
                .where(Run.id == run_id)
                .values(
                    finished_at=func.now(),
                    fetched_count=fetched,
                    new_count=new,
                    notified_count=notified,
                    error=error,
                )
            )
            await session.commit()

        log.info(
            "pipeline done",
            run_id=run_id,
            fetched=fetched,
            new=new,
            notified=notified,
            error=error,
        )


async def run_once() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    log_ = structlog.get_logger("job_scanner")
    log_.info("job-scanner: config loaded", **settings.safe_dump())

    await pipeline()


if __name__ == "__main__":
    asyncio.run(run_once())
