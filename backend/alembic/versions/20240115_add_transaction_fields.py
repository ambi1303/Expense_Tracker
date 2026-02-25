"""Add category, payment_method, upi_reference, raw_snippet to transactions

Revision ID: 20240115_add_fields
Revises: ff4c1e7fcf3b
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20240115_add_fields'
down_revision = 'ff4c1e7fcf3b'
branch_labels = None
depends_on = None


def upgrade():
    """Add new fields to transactions table."""
    # Add category field (indexed for filtering)
    op.add_column('transactions', sa.Column('category', sa.String(100), nullable=True))
    
    # Add payment_method field
    op.add_column('transactions', sa.Column('payment_method', sa.String(50), nullable=True))
    
    # Add upi_reference field (indexed for searching)
    op.add_column('transactions', sa.Column('upi_reference', sa.String(255), nullable=True))
    
    # Add raw_snippet field for debugging
    op.add_column('transactions', sa.Column('raw_snippet', sa.String(500), nullable=True))
    
    # Add indexes for frequently queried fields
    op.create_index('ix_transactions_category', 'transactions', ['category'])
    op.create_index('ix_transactions_upi_reference', 'transactions', ['upi_reference'])


def downgrade():
    """Remove new fields from transactions table."""
    # Drop indexes first
    op.drop_index('ix_transactions_upi_reference', 'transactions')
    op.drop_index('ix_transactions_category', 'transactions')
    
    # Drop columns
    op.drop_column('transactions', 'raw_snippet')
    op.drop_column('transactions', 'upi_reference')
    op.drop_column('transactions', 'payment_method')
    op.drop_column('transactions', 'category')
