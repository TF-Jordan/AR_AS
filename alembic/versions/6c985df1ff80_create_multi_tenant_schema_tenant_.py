"""Create multi-tenant schema (Tenant, ScoringConfig, ProductDescription)

Revision ID: 6c985df1ff80
Revises:
Create Date: 2026-02-11 13:05:41.045000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6c985df1ff80'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the multi-tenant tables: tenants, scoring_configs, product_descriptions."""

    # ---- tenants ----
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(100), nullable=True),
        sa.Column('keycloak_client_id', sa.String(100), nullable=True),
        sa.Column('qdrant_collection_name', sa.String(100), nullable=False),
        sa.Column('rate_limit_requests', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('rate_limit_window_seconds', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_tenants_tenant_id', 'tenants', ['tenant_id'], unique=True)
    op.create_index('ix_tenants_is_active', 'tenants', ['is_active'])
    op.create_index('ix_tenants_keycloak_client_id', 'tenants', ['keycloak_client_id'], unique=True)

    # ---- scoring_configs ----
    op.create_table(
        'scoring_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(100), sa.ForeignKey('tenants.tenant_id', ondelete='CASCADE'), nullable=False),
        sa.Column('scoring_criteria', postgresql.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(255), nullable=True),
    )
    op.create_index('ix_scoring_configs_tenant_id', 'scoring_configs', ['tenant_id'])
    op.create_index('ix_scoring_configs_is_active', 'scoring_configs', ['is_active'])
    # Partial unique index: only one active config per tenant
    op.create_index(
        'ix_scoring_configs_active_tenant',
        'scoring_configs',
        ['tenant_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true'),
    )

    # ---- product_descriptions ----
    op.create_table(
        'product_descriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(100), sa.ForeignKey('tenants.tenant_id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('vector_embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('embedding_model', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_vectorized_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_product_descriptions_tenant_id', 'product_descriptions', ['tenant_id'])
    op.create_index('ix_product_descriptions_product_id', 'product_descriptions', ['product_id'])
    op.create_unique_constraint('uq_tenant_product', 'product_descriptions', ['tenant_id', 'product_id'])


def downgrade() -> None:
    """Drop the multi-tenant tables."""
    op.drop_table('product_descriptions')
    op.drop_table('scoring_configs')
    op.drop_table('tenants')
