from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class RawJob:
    source: str
    external_id: Optional[str]
    title: str
    url: str
    description: Optional[str] = None
    tags: list = field(default_factory=list)
    budget: Optional[str] = None
    posted_at: Optional[datetime] = None
    raw: dict = field(default_factory=dict)


class BaseSource(abc.ABC):
    name: str
    type: str

    @abc.abstractmethod
    async def fetch(self) -> list[RawJob]:
        """Получить сырые вакансии из источника."""
