from __future__ import annotations

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = structlog.get_logger("http")


def _log_retry(state) -> None:
    log.warning("retrying http", attempt=state.attempt_number, url=state.args[0] if state.args else "?")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.HTTPError),
    before_sleep=_log_retry,
    reraise=True,
)
async def fetch_json(
    url: str,
    headers: dict | None = None,
    timeout: int = 20,
) -> object:
    """GET url → JSON. При httpx.HTTPError ретраит до 3 раз с backoff."""
    async with httpx.AsyncClient(
        timeout=timeout,
        headers=headers or {},
        follow_redirects=True,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()
