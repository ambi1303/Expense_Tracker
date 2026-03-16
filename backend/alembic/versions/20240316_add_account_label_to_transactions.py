"""Add account_label to transactions for multi-account/card support

Revision ID: 20240316_account_label
Revises: 20240115_add_fields
Create Date: 2024-03-16

"""
from alembic import op
import sqlalchemy as sa


revision = '20240316_account_label'
down_revision = '20240115_add_updated_at'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('transactions', sa.Column('account_label', sa.String(128), nullable=True))
    op.create_index('ix_transactions_account_label', 'transactions', ['account_label'])


def downgrade():
    op.drop_index('ix_transactions_account_label', 'transactions')
    op.drop_column('transactions', 'account_label')
