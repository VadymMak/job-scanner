from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from app.core.http import fetch_json
from app.sources.base import BaseSource, RawJob

_UA = "job-scanner/0.1 (personal aggregator; contact: vadym)"
_API_URL = "https://remoteok.com/api"


class RemoteOKSource(BaseSource):
    name = "remoteok"
    type = "api"

    async def fetch(self) -> list[RawJob]:
        data = await fetch_json(_API_URL, headers={"User-Agent": _UA})

        jobs: list[RawJob] = []
        for item in data:
            # Первый элемент — юридическая пометка без поля "id", пропускаем
            if "id" not in item:
                continue
            jobs.append(_parse(item))
        return jobs


def _parse(item: dict) -> RawJob:
    external_id = str(item.get("id", ""))

    company = item.get("company") or ""
    position = item.get("position") or item.get("title") or ""
    title = f"{position} @ {company}" if company else position

    url = item.get("url") or item.get("apply_url") or ""

    description: Optional[str] = item.get("description") or None

    tags: list[str] = item.get("tags") or []

    budget: Optional[str] = None
    sal_min = item.get("salary_min")
    sal_max = item.get("salary_max")
    if sal_min and sal_max:
        budget = f"{sal_min}–{sal_max} USD"
    elif sal_min:
        budget = f"from {sal_min} USD"
    elif sal_max:
        budget = f"up to {sal_max} USD"

    posted_at: Optional[datetime] = None
    epoch = item.get("epoch")
    if epoch:
        posted_at = datetime.fromtimestamp(int(epoch), tz=timezone.utc)

    return RawJob(
        source="remoteok",
        external_id=external_id,
        title=title,
        url=url,
        description=description,
        tags=tags,
        budget=budget,
        posted_at=posted_at,
        raw=item,
    )


if __name__ == "__main__":
    async def _main() -> None:
        source = RemoteOKSource()
        jobs = await source.fetch()
        print(f"\n Получено вакансий: {len(jobs)}\n")
        for job in jobs[:3]:
            print(f"  [{job.external_id}] {job.title}")
            print(f"  URL:    {job.url}")
            print(f"  Теги:   {job.tags[:5]}")
            print(f"  Бюджет: {job.budget}")
            print(f"  Дата:   {job.posted_at}")
            print()

    asyncio.run(_main())
