"""Add HNSW index, BM25 index, and RLS policies

Revision ID: 002
Revises: 001
Create Date: 2026-03-11
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # HNSW index for vector similarity search
    op.execute(
        "CREATE INDEX chunks_embedding_hnsw_idx ON chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # pg_search BM25 index (pg_search 0.21+ uses native CREATE INDEX syntax)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
    op.execute(
        "CREATE INDEX chunks_bm25_idx ON chunks "
        "USING bm25 (id, content) "
        "WITH (key_field = 'id')"
    )

    # Enable RLS on tenant tables
    for table in ("knowledge_bases", "documents", "chunks", "conversations", "messages"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_isolation ON {table}
            USING (user_id::text = current_setting('app.current_user_id', true))
        """)


def downgrade() -> None:
    for table in ("messages", "conversations", "chunks", "documents", "knowledge_bases"):
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP INDEX IF EXISTS chunks_bm25_idx")
    op.execute("DROP INDEX IF EXISTS chunks_embedding_hnsw_idx")
