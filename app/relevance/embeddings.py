from __future__ import annotations

import structlog
from openai import AsyncOpenAI
from sqlalchemy import select, update

from app.config import get_settings
from app.db.models import Job, JobStatus
from app.db.session import AsyncSessionLocal

log = structlog.get_logger("embeddings")

EMBED_MODEL = "text-embedding-3-small"
BATCH = 100

client = AsyncOpenAI(api_key=get_settings().openai_api_key)


def _job_text(job: Job) -> str:
    """Склеить title, tags и начало description в одну строку для эмбеддинга."""
    parts: list[str] = []
    if job.title:
        parts.append(job.title)
    if job.tags:
        parts.append(" ".join(job.tags))
    if job.description:
        parts.append(job.description[:2000])
    return " ".join(parts)


async def embed_pending_jobs() -> dict:
    """Получить эмбеддинги для всех вакансий без embedding и сохранить в БД."""
    async with AsyncSessionLocal() as session:
        # Реактивируем ранее отсеянные вакансии — теперь все идут через эмбеддинг
        await session.execute(
            update(Job)
            .where(Job.status == JobStatus.skipped)
            .values(status=JobStatus.new)
        )
        await session.commit()

        # Берём все вакансии без эмбеддинга
        result = await session.execute(
            select(Job).where(Job.embedding.is_(None))
        )
        jobs = result.scalars().all()

    if not jobs:
        log.info("embed_pending_jobs: ничего для обработки")
        return {"embedded": 0}

    embedded = 0
    for start in range(0, len(jobs), BATCH):
        chunk = jobs[start : start + BATCH]
        texts = [_job_text(j) for j in chunk]

        response = await client.embeddings.create(model=EMBED_MODEL, input=texts)

        async with AsyncSessionLocal() as session:
            for i, job in enumerate(chunk):
                # Получаем "живой" объект в текущей сессии по id
                db_job = await session.get(Job, job.id)
                if db_job is not None:
                    db_job.embedding = response.data[i].embedding
            await session.commit()

        embedded += len(chunk)
        log.info("embed batch done", batch_start=start, count=len(chunk))

    stats = {"embedded": embedded}
    log.info("embed_pending_jobs done", **stats)
    return stats
