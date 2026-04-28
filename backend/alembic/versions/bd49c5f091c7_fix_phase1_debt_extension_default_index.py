"""fix_phase1_debt_extension_default_index

Revision ID: bd49c5f091c7
Revises: 23beccb1c3be
Create Date: 2026-04-27 20:37:24.660807

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision: str = 'bd49c5f091c7'
down_revision: Union[str, None] = '23beccb1c3be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Debt #1: Ensure pgvector extension exists (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Debt #2: Add server_default for is_ordered column
    op.alter_column(
        "surveys",
        "is_ordered",
        server_default=sa.text("true"),
    )

    # Debt #3: Create HNSW index for cosine similarity searches on prompt_embedding
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_survey_cache_embedding_hnsw "
        "ON survey_cache USING hnsw (prompt_embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_survey_cache_embedding_hnsw")
    op.alter_column("surveys", "is_ordered", server_default=None)
    op.execute("DROP EXTENSION IF EXISTS vector")
