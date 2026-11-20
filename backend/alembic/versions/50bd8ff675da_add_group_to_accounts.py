"""add group to accounts

Revision ID: 50bd8ff675da
Revises: 095fd0b06881
Create Date: 2026-11-20 18:56:09.737837

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "50bd8ff675da"
down_revision: str | Sequence[str] | None = "095fd0b06881"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    The default only files the accounts that already exist under "Other"; it is dropped straight
    after, so a new account must always name its group.
    """
    op.add_column(
        "accounts",
        sa.Column("group_name", sa.String(), nullable=False, server_default="Other"),
    )
    op.alter_column("accounts", "group_name", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("accounts", "group_name")
