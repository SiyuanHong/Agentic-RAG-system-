"""Add skills table with RLS

Revision ID: 003
Revises: 002
Create Date: 2026-03-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_skills_user_id", "skills", ["user_id"])

    # RLS
    op.execute("ALTER TABLE skills ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY skills_isolation ON skills
        USING (user_id::text = current_setting('app.current_user_id', true))
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS skills_isolation ON skills")
    op.execute("ALTER TABLE skills DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_skills_user_id")
    op.drop_table("skills")
