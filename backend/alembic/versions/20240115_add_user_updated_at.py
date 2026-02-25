"""Add updated_at to users

Revision ID: 20240115_add_updated_at
Revises: 20240115_add_fields
Create Date: 2024-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


# revision identifiers, used by Alembic.
revision = '20240115_add_updated_at'
down_revision = '20240115_add_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Add updated_at column to users table."""
    # Add column with default value
    op.add_column('users',
        sa.Column('updated_at',
                 sa.DateTime(timezone=True),
                 nullable=False,
                 server_default=sa.text('CURRENT_TIMESTAMP'))
    )


def downgrade():
    """Remove updated_at column from users table."""
    op.drop_column('users', 'updated_at')
