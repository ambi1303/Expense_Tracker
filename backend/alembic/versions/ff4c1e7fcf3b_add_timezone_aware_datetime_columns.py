"""add_timezone_aware_datetime_columns

Revision ID: ff4c1e7fcf3b
Revises: a8daafe2b7f5
Create Date: 2026-02-19 20:57:59.261623

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff4c1e7fcf3b'
down_revision: Union[str, None] = 'a8daafe2b7f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert all DateTime columns to timezone-aware (TIMESTAMPTZ in PostgreSQL)
    # PostgreSQL will automatically convert existing TIMESTAMP to TIMESTAMPTZ
    
    # Update users table
    op.execute("ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'")
    
    # Update transactions table
    op.execute("ALTER TABLE transactions ALTER COLUMN transaction_date TYPE TIMESTAMPTZ USING transaction_date AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE transactions ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'")
    
    # Update sync_logs table
    op.execute("ALTER TABLE sync_logs ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'")


def downgrade() -> None:
    # Revert to naive TIMESTAMP (without timezone)
    
    # Revert users table
    op.execute("ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP USING created_at AT TIME ZONE 'UTC'")
    
    # Revert transactions table
    op.execute("ALTER TABLE transactions ALTER COLUMN transaction_date TYPE TIMESTAMP USING transaction_date AT TIME ZONE 'UTC'")
    op.execute("ALTER TABLE transactions ALTER COLUMN created_at TYPE TIMESTAMP USING created_at AT TIME ZONE 'UTC'")
    
    # Revert sync_logs table
    op.execute("ALTER TABLE sync_logs ALTER COLUMN created_at TYPE TIMESTAMP USING created_at AT TIME ZONE 'UTC'")
