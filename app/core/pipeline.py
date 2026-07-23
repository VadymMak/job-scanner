import structlog
from sqlalchemy import select

from app.core.normalize import normalize
from app.db.models import Job, Source
from app.db.session import AsyncSessionLocal
from app.sources.base import BaseSource

log = structlog.get_logger("pipeline")


async def ingest(source: BaseSource) -> dict:
    raw = await source.fetch()

    async with AsyncSessionLocal() as session:
        # --- get-or-create Source ---
        result = await session.execute(
            select(Source).where(Source.name == source.name)
        )
        src = result.scalar_one_or_none()
        if src is None:
            src = Source(name=source.name, type=source.type, config={})
            session.add(src)
            await session.flush()  # получаем src.id до commit

        # --- нормализация ---
        normalized = [normalize(r) for r in raw]
        hashes = [n["hash"] for n in normalized]

        # --- существующие хеши из БД ---
        existing_result = await session.execute(
            select(Job.hash).where(Job.hash.in_(hashes))
        )
        existing: set[str] = set(existing_result.scalars())

        # --- вставка новых ---
        new_count = 0
        for n in normalized:
            h = n["hash"]
            if h in existing:
                continue
            session.add(Job(source_id=src.id, **n))
            existing.add(h)  # защита от дублей внутри пачки
            new_count += 1

        await session.commit()

    stats = {"fetched": len(raw), "new": new_count}
    log.info("ingest done", source=source.name, **stats)
    return stats
