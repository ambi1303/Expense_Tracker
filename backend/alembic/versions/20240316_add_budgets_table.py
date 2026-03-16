"""Add budgets table

Revision ID: 20240316_budgets
Revises: 20240316_account_label
Create Date: 2024-03-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = '20240316_budgets'
down_revision = '20240316_account_label'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'budgets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('period', sa.String(20), default='monthly', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_budgets_user_id', 'budgets', ['user_id'])
    op.create_index('ix_budgets_category', 'budgets', ['category'])


def downgrade():
    op.drop_index('ix_budgets_category', 'budgets')
    op.drop_index('ix_budgets_user_id', 'budgets')
    op.drop_table('budgets')
