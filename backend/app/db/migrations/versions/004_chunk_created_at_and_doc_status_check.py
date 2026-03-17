"""Add created_at to chunks + CHECK constraint on document status

Revision ID: 004
Revises: 003
Create Date: 2026-03-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, Sequence[str], None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add created_at timestamp to chunks table
    op.add_column(
        "chunks",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )

    # Add CHECK constraint on document status
    op.create_check_constraint(
        "ck_documents_status",
        "documents",
        sa.column("status").in_(["pending", "processing", "completed", "failed"]),
    )


def downgrade() -> None:
    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.drop_column("chunks", "created_at")
