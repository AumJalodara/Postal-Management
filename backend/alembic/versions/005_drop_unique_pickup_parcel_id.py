"""drop_unique_pickup_parcel_id

Revision ID: 005_pickup_rebook
Revises: 146331d49b8c
Create Date: 2026-10-22 15:32:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '005_pickup_rebook'
down_revision: Union[str, None] = '146331d49b8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        # Drop unique constraint on parcel_id and create index
        op.drop_constraint('pickup_requests_parcel_id_key', 'pickup_requests', type_='unique')
        op.create_index(op.f('ix_pickup_requests_parcel_id'), 'pickup_requests', ['parcel_id'], unique=False)
    else:
        # SQLite batch mode
        with op.batch_alter_table('pickup_requests') as batch_op:
            batch_op.drop_constraint('uq_pickup_requests_parcel_id', type_='unique')
            batch_op.create_index(batch_op.f('ix_pickup_requests_parcel_id'), ['parcel_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.drop_index(op.f('ix_pickup_requests_parcel_id'), table_name='pickup_requests')
        op.create_unique_constraint('pickup_requests_parcel_id_key', 'pickup_requests', ['parcel_id'])
    else:
        with op.batch_alter_table('pickup_requests') as batch_op:
            batch_op.drop_index(batch_op.f('ix_pickup_requests_parcel_id'))
            batch_op.create_unique_constraint('uq_pickup_requests_parcel_id', ['parcel_id'])
