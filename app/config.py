from __future__ import annotations

from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Database ---
    database_url: str = (
        "postgresql+psycopg://scanner:scanner@127.0.0.1:5432/job_scanner"
    )

    # --- Telegram (опционально) ---
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # --- LLM (опционально) ---
    llm_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None  # читается из OPENAI_API_KEY в окружении
    llm_model: str = "gpt-4o-mini"

    # --- Приложение ---
    log_level: str = "INFO"
    poll_interval_seconds: int = 900  # 15 минут
    notify_threshold: int = 65  # минимальный relevance_score для отправки в Telegram

    def safe_dump(self) -> dict:
        """Конфиг без секретов — безопасно логировать."""
        parsed = urlparse(self.database_url)
        db_safe = f"{parsed.scheme}://***@{parsed.hostname}{parsed.path}"

        return {
            "database": db_safe,
            "telegram_bot_token": "***" if self.telegram_bot_token else None,
            "telegram_chat_id": self.telegram_chat_id,
            "llm_api_key": "***" if self.llm_api_key else None,
            "openai_api_key": "***" if self.openai_api_key else None,
            "llm_model": self.llm_model,
            "log_level": self.log_level,
            "poll_interval_seconds": self.poll_interval_seconds,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
