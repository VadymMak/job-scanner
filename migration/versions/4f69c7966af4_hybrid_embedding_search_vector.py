"""hybrid: embedding + search_vector

Revision ID: 4f69c7966af4
Revises: 2c84e7d0ac1a
Create Date: 2026-07-23 19:03:48.908715

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '4f69c7966af4'
down_revision: Union[str, Sequence[str], None] = '2c84e7d0ac1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Колонка с эмбеддингом: обычная nullable, заполняется на шаге 2.3
    op.add_column("jobs", sa.Column("embedding", Vector(1536), nullable=True))

    # Генерируемая колонка: Postgres сам пересчитывает при каждом INSERT/UPDATE.
    # Alembic не умеет её создавать через op.add_column — используем raw SQL.
    op.execute(
        "ALTER TABLE jobs ADD COLUMN search_vector tsvector "
        "GENERATED ALWAYS AS ("
        "  to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,''))"
        ") STORED"
    )

    # GIN-индекс — оптимален для tsvector и полнотекстового поиска (@@)
    op.execute(
        "CREATE INDEX ix_jobs_search_vector ON jobs USING gin (search_vector)"
    )

    # HNSW-индекс для приближённого поиска ближайших векторов.
    # vector_cosine_ops = косинусное расстояние (подходит для эмбеддингов OpenAI)
    op.execute(
        "CREATE INDEX ix_jobs_embedding ON jobs USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_jobs_embedding")
    op.execute("DROP INDEX IF EXISTS ix_jobs_search_vector")
    # search_vector — GENERATED колонка, нельзя менять через op.drop_column
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS search_vector")
    op.drop_column("jobs", "embedding")
