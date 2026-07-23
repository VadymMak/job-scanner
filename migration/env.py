from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# --- Наши модули ---
# Импорт моделей обязателен: без него Alembic не знает о таблицах
import app.db.models  # noqa: F401 — регистрирует Source, Job, Run, Notification
from app.db.base import Base
from app.config import get_settings

# Alembic config object
config = context.config

# Логирование из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Подставляем URL из наших настроек (читает .env)
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# Метаданные всех наших таблиц — именно по ним autogenerate строит миграции
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline-режим: генерирует SQL-скрипт без реального подключения к БД."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online-режим: подключается к БД и применяет миграции напрямую."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
