import hashlib


def job_hash(source: str, external_id: str | None, url: str) -> str:
    """SHA-256 от 'source:external_id' или 'source:url' если нет external_id."""
    key = f"{source}:{external_id or url}"
    return hashlib.sha256(key.encode()).hexdigest()
