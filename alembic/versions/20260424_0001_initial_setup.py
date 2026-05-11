"""Initial setup — enable pgvector and utility extensions

Revision ID: 0001
Revises:
Create Date: 2026-04-24 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgvector: vector similarity search
    # TODO: Re-enable when pgvector is available on the Postgres instance
    # op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # uuid-ossp: UUID generation functions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    # pg_trgm: trigram similarity for text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # btree_gin: GIN index support for btree operators
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")


def downgrade() -> None:
    # Extensions are intentionally left in place on downgrade
    pass
