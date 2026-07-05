"""add cancelled request status

Revision ID: b160868a1836
Revises: c63bbc8ec4c6
Create Date: 2026-07-05 06:26:36.538410

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b160868a1836'
down_revision: Union[str, None] = 'c63bbc8ec4c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE requeststatus ADD VALUE 'cancelled'")


def downgrade() -> None:
    op.execute("ALTER TYPE requeststatus RENAME TO requeststatus_old")
    op.execute("CREATE TYPE requeststatus AS ENUM ('pending', 'processing', 'completed', 'failed')")
    op.execute(
        "ALTER TABLE document_requests "
        "ALTER COLUMN status TYPE requeststatus "
        "USING status::text::requeststatus"
    )
    op.execute("DROP TYPE requeststatus_old")
