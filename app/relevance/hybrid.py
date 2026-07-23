from __future__ import annotations

import structlog
from sqlalchemy import func, select

from app.db.models import Job, JobStatus
from app.db.session import AsyncSessionLocal
from app.relevance.embeddings import EMBED_MODEL, client
from app.relevance.profile import PROFILE_QUERY, PROFILE_TEXT

log = structlog.get_logger("hybrid")

RRF_K = 60
TOP_N = 20


async def _embed_profile() -> list[float]:
    """Один вызов API — получаем вектор профиля разработчика."""
    resp = await client.embeddings.create(model=EMBED_MODEL, input=[PROFILE_TEXT])
    return resp.data[0].embedding


async def rank_candidates(top_n: int = TOP_N) -> list[dict]:
    """
    Ранжировать new-вакансии через RRF по двум сигналам:
      - semantic: косинусное расстояние эмбеддинга вакансии к профилю
      - lexical:  ts_rank по полнотекстовому индексу
    Возвращает топ top_n кандидатов отсортированных по rrf desc.
    """
    profile_vec = await _embed_profile()

    async with AsyncSessionLocal() as session:
        # --- Семантический ранг ---
        # cosine_distance: чем меньше, тем ближе → ORDER BY ASC = лучшие первые
        sem_result = await session.execute(
            select(Job.id)
            .where(Job.status == JobStatus.new, Job.embedding.is_not(None))
            .order_by(Job.embedding.cosine_distance(profile_vec))
        )
        sem_ids: list[int] = list(sem_result.scalars())
        sem_rank: dict[int, int] = {job_id: i + 1 for i, job_id in enumerate(sem_ids)}

        # --- Лексический ранг ---
        # ts_rank: чем больше, тем релевантнее → ORDER BY DESC = лучшие первые
        lex_result = await session.execute(
            select(Job.id)
            .where(Job.status == JobStatus.new)
            .order_by(
                func.ts_rank(
                    Job.search_vector,
                    func.to_tsquery("english", PROFILE_QUERY),
                ).desc()
            )
        )
        lex_ids: list[int] = list(lex_result.scalars())
        lex_rank: dict[int, int] = {job_id: i + 1 for i, job_id in enumerate(lex_ids)}

    # --- RRF слияние ---
    all_ids = set(sem_rank) | set(lex_rank)
    candidates: list[dict] = []
    for job_id in all_ids:
        rrf = 0.0
        if job_id in sem_rank:
            rrf += 1.0 / (RRF_K + sem_rank[job_id])
        if job_id in lex_rank:
            rrf += 1.0 / (RRF_K + lex_rank[job_id])
        candidates.append(
            {
                "id": job_id,
                "rrf": round(rrf, 6),
                "sem_rank": sem_rank.get(job_id),
                "lex_rank": lex_rank.get(job_id),
            }
        )

    candidates.sort(key=lambda x: x["rrf"], reverse=True)
    top = candidates[:top_n]

    log.info(
        "hybrid rank done",
        total_candidates=len(candidates),
        top_n=len(top),
        top5=[
            f"id={c['id']} rrf={c['rrf']} sem={c['sem_rank']} lex={c['lex_rank']}"
            for c in top[:5]
        ],
    )
    return top
