from app.core.dedupe import job_hash
from app.sources.base import RawJob


def normalize(raw: RawJob) -> dict:
    """Преобразует RawJob в словарь колонок таблицы jobs (без source_id)."""
    return {
        "external_id": raw.external_id,
        "hash": job_hash(raw.source, raw.external_id, raw.url),
        "title": raw.title,
        "description": raw.description,
        "url": raw.url,
        "tags": raw.tags,
        "budget": raw.budget,
        "posted_at": raw.posted_at,
    }
