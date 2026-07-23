from __future__ import annotations

import re

import structlog
from sqlalchemy import select

from app.db.models import Job, JobStatus
from app.db.session import AsyncSessionLocal

log = structlog.get_logger("prefilter")

# Темы и их ключевые слова
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "ai-integrations": [
        "ai", "llm", "gpt", "rag", "embedding", "embeddings",
        "openai", "anthropic", "langchain", "vector", "chatbot",
        "machine learning", "ml", "mcp", "prompt", "nlp",
    ],
    "fullstack-js-ts": [
        "react", "next.js", "nextjs", "node", "node.js", "typescript",
        "javascript", "full stack", "full-stack", "fullstack",
        "frontend", "backend", "vue",
    ],
}

# Предкомпиляция: {topic: [compiled_pattern, ...]}
_PATTERNS: dict[str, list[re.Pattern]] = {
    topic: [
        re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
        for kw in keywords
    ]
    for topic, keywords in TOPIC_KEYWORDS.items()
}


def matched_topics(text: str) -> list[str]:
    """Вернуть список тем, для которых хотя бы одно ключевое слово найдено в тексте."""
    result = []
    for topic, patterns in _PATTERNS.items():
        for pattern in patterns:
            if pattern.search(text):
                result.append(topic)
                break  # одно совпадение по теме достаточно
    return result


async def prefilter_new_jobs() -> dict:
    """Аннотировать new-вакансии matched_topics. Статус не меняем — все идут дальше."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Job).where(Job.status == JobStatus.new)
        )
        jobs = result.scalars().all()

        checked = kept = 0
        for job in jobs:
            parts = [job.title or ""]
            if job.tags:
                parts.append(" ".join(job.tags))
            if job.description:
                parts.append(job.description)
            text = " ".join(parts)

            topics = matched_topics(text)
            job.matched_topics = topics
            checked += 1
            kept += 1

        await session.commit()

    stats = {"checked": checked, "kept": kept, "skipped": 0}
    log.info("prefilter done", **stats)
    return stats
