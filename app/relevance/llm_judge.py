from __future__ import annotations

import asyncio
import json

import structlog
from sqlalchemy import select

from app.config import get_settings
from app.db.models import Job, JobStatus
from app.db.session import AsyncSessionLocal
from app.relevance.embeddings import client
from app.relevance.profile import PROFILE_TEXT

log = structlog.get_logger("llm_judge")

VERDICT_SCHEMA = {
    "name": "verdict",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "description": "Релевантность вакансии специалисту, 0-100",
            },
            "matched_topics": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Темы из профиля, которые есть в вакансии",
            },
            "reason": {
                "type": "string",
                "description": "Одно предложение по-русски — почему этот балл",
            },
        },
        "required": ["score", "matched_topics", "reason"],
        "additionalProperties": False,
    },
}

_SYSTEM = (
    "Ты оцениваешь, насколько вакансия подходит вот этому специалисту:\n\n"
    f"{PROFILE_TEXT}\n\n"
    "Темы: AI-интеграции и Full-stack JS/TS. "
    "Верни score 0-100 (насколько заказ релевантен его стеку/интересам), "
    "matched_topics (список тем из профиля, которые есть в вакансии) "
    "и reason одной строкой по-русски."
)


async def _judge(job: Job) -> dict:
    """Один запрос к LLM — оценить одну вакансию."""
    tags_str = ", ".join(job.tags) if job.tags else ""
    desc = (job.description or "")[:1500]
    user_text = f"Вакансия: {job.title}\nТеги: {tags_str}\nОписание: {desc}"

    resp = await client.chat.completions.create(
        model=get_settings().llm_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_text},
        ],
        response_format={"type": "json_schema", "json_schema": VERDICT_SCHEMA},
    )
    return json.loads(resp.choices[0].message.content)


async def score_top_candidates(top: list[dict]) -> dict:
    """Отправить топ-N кандидатов в LLM параллельно, сохранить оценки в БД."""
    if not top:
        log.info("score_top_candidates: нет кандидатов")
        return {"scored": 0}

    top_ids = [c["id"] for c in top]

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Job).where(Job.id.in_(top_ids)))
        jobs = result.scalars().all()

    # Параллельные запросы к GPT — все вакансии сразу
    verdicts = await asyncio.gather(*[_judge(job) for job in jobs])

    async with AsyncSessionLocal() as session:
        for job, verdict in zip(jobs, verdicts):
            db_job = await session.get(Job, job.id)
            if db_job is None:
                continue
            db_job.relevance_score = int(verdict["score"])
            db_job.relevance_reason = verdict["reason"]
            db_job.matched_topics = verdict["matched_topics"]
            db_job.status = JobStatus.scored
        await session.commit()

    scored = len(jobs)
    log.info("score_top_candidates done", scored=scored)
    return {"scored": scored}
