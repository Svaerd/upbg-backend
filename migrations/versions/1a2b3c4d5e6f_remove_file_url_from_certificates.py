"""remove file_url from certificates

Revision ID: 1a2b3c4d5e6f
Revises: b2975d4852ca
Create Date: 2026-06-18 14:31:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "b2975d4852ca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the file_url column from the certificates table
    op.execute("ALTER TABLE certificates DROP COLUMN file_url;")


def downgrade() -> None:
    # Add the file_url column back if we need to rollback
    op.execute("ALTER TABLE certificates ADD COLUMN file_url VARCHAR(255);")
