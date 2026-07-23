from __future__ import annotations

import asyncio
import html

import structlog
from aiogram import Bot
from sqlalchemy import select

from app.config import get_settings
from app.db.models import Job, JobStatus, Notification
from app.db.session import AsyncSessionLocal

log = structlog.get_logger("telegram")


def _format(job: Job) -> str:
    """Сформировать HTML-сообщение для Telegram."""
    title = html.escape(job.title or "")
    reason = html.escape(job.relevance_reason or "")
    topics = html.escape(", ".join(job.matched_topics) if job.matched_topics else "—")
    url = job.url or ""
    score = job.relevance_score or 0

    lines = [
        f"🔹 <b>{title}</b> — {score}/100",
        reason,
    ]
    if job.budget:
        lines.append(f"💰 {html.escape(job.budget)}")
    lines.append(f"🏷 {topics}")
    lines.append(f"🔗 {url}")

    return "\n".join(lines)


async def notify_scored() -> dict:
    """Отправить все scored-вакансии выше порога в Telegram."""
    settings = get_settings()

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        log.warning("telegram: token или chat_id не настроены — пропускаем")
        return {"sent": 0}

    bot = Bot(token=settings.telegram_bot_token)
    sent = 0

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Job)
                .where(
                    Job.status == JobStatus.scored,
                    Job.relevance_score >= settings.notify_threshold,
                )
                .order_by(Job.relevance_score.desc())
            )
            jobs = result.scalars().all()

            for job in jobs:
                msg = await bot.send_message(
                    chat_id=settings.telegram_chat_id,
                    text=_format(job),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                session.add(
                    Notification(
                        job_id=job.id,
                        channel="telegram",
                        message_id=str(msg.message_id),
                    )
                )
                job.status = JobStatus.notified
                sent += 1
                await asyncio.sleep(0.3)

            await session.commit()

    finally:
        await bot.session.close()

    log.info("notify_scored done", sent=sent, threshold=settings.notify_threshold)
    return {"sent": sent}
