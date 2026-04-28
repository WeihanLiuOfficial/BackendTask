"""add_quality_issues_column

Revision ID: bcd8398dc1a7
Revises: 89a1da1104f9
Create Date: 2026-04-27 23:10:29.196781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bcd8398dc1a7'
down_revision: Union[str, None] = '89a1da1104f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOTE: Manually removed false-positive op.drop_index('ix_survey_cache_embedding_hnsw').
    # Alembic cannot detect pgvector HNSW indexes — this is a known issue.
    op.add_column('surveys', sa.Column('quality_issues', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('surveys', 'quality_issues')
