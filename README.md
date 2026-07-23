# job-scanner

Личный сканер вакансий: агрегирует вакансии из нескольких источников,
оценивает релевантность через LLM и отправляет уведомления в Telegram.

## Быстрый старт

```bash
cp .env.example .env      # заполни реальными значениями
source .venv/bin/activate
python -m app.main        # smoke-тест
```

## Структура

```
app/
  config.py      — настройки через pydantic-settings
  main.py        — точка входа
  sources/       — адаптеры источников вакансий (шаг 2)
  core/          — доменные модели (шаг 2)
  db/            — SQLAlchemy / Alembic (шаг 3)
  relevance/     — оценка через LLM (шаг 4)
  notify/        — Telegram-уведомления (шаг 5)
```
