"""Add products table for multi-tenant product catalog

Revision ID: a1b2c3d4e5f6
Revises: 6c985df1ff80
Create Date: 2026-02-13 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6c985df1ff80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the products table for storing tenant product catalogs."""

    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.String(255), nullable=False, comment='External product ID from tenant system'),
        sa.Column('name', sa.String(500), nullable=False, comment='Product name'),
        sa.Column('description', sa.Text(), nullable=True, comment='Product description'),
        sa.Column('category', sa.String(255), nullable=True, comment='Product category'),
        sa.Column('sku', sa.String(255), nullable=True, comment='Stock keeping unit'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Indexes for efficient queries
    op.create_index('ix_products_tenant_id', 'products', ['tenant_id'])
    op.create_index('ix_products_product_id', 'products', ['product_id'])
    op.create_index('ix_products_name', 'products', ['name'])
    op.create_index('ix_products_category', 'products', ['category'])

    # Unique constraint: one product_id per tenant
    op.create_unique_constraint('uq_tenant_product_catalog', 'products', ['tenant_id', 'product_id'])


def downgrade() -> None:
    """Drop the products table."""
    op.drop_table('products')
