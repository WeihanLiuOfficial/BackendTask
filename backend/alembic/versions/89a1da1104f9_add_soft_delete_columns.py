"""add_soft_delete_columns

Revision ID: 89a1da1104f9
Revises: bd49c5f091c7
Create Date: 2026-04-27 21:04:41.220409

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision: str = '89a1da1104f9'
down_revision: Union[str, None] = 'bd49c5f091c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('surveys', sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('surveys', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('surveys', 'deleted_at')
    op.drop_column('surveys', 'is_deleted')
