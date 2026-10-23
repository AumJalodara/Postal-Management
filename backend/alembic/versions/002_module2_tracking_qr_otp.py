"""module 2 tracking qr otp migration

Revision ID: 002_module2_tracking_qr_otp
Revises: 001_initial_module1
Create Date: 2026-09-09 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_module2_tracking_qr_otp'
down_revision: Union[str, None] = '001_initial_module1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add status column to parcels table
    op.add_column(
        'parcels',
        sa.Column('status', sa.String(length=50), nullable=False, server_default='BOOKED')
    )
    op.create_index(op.f('ix_parcels_status'), 'parcels', ['status'], unique=False)

    # 2. Create parcel_tracking_events table
    op.create_table(
        'parcel_tracking_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parcel_id', sa.Integer(), nullable=False),
        sa.Column('previous_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('location_label', sa.String(length=150), nullable=False),
        sa.Column('description', sa.String(length=300), nullable=False),
        sa.Column('actor_type', sa.String(length=50), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parcel_id'], ['parcels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_parcel_tracking_events_id'), 'parcel_tracking_events', ['id'], unique=False)
    op.create_index(op.f('ix_parcel_tracking_events_parcel_id'), 'parcel_tracking_events', ['parcel_id'], unique=False)
    op.create_index(op.f('ix_parcel_tracking_events_new_status'), 'parcel_tracking_events', ['new_status'], unique=False)
    op.create_index(op.f('ix_parcel_tracking_events_created_at'), 'parcel_tracking_events', ['created_at'], unique=False)

    # 3. Create parcel_qr_codes table
    op.create_table(
        'parcel_qr_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parcel_id', sa.Integer(), nullable=False),
        sa.Column('qr_token', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['parcel_id'], ['parcels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('qr_token')
    )
    op.create_index(op.f('ix_parcel_qr_codes_id'), 'parcel_qr_codes', ['id'], unique=False)
    op.create_index(op.f('ix_parcel_qr_codes_parcel_id'), 'parcel_qr_codes', ['parcel_id'], unique=False)
    op.create_index(op.f('ix_parcel_qr_codes_qr_token'), 'parcel_qr_codes', ['qr_token'], unique=True)

    # 4. Create delivery_otps table
    op.create_table(
        'delivery_otps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parcel_id', sa.Integer(), nullable=False),
        sa.Column('otp_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default=sa.text('5')),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['parcel_id'], ['parcels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_otps_id'), 'delivery_otps', ['id'], unique=False)
    op.create_index(op.f('ix_delivery_otps_parcel_id'), 'delivery_otps', ['parcel_id'], unique=False)

    # 5. Create postal_locations reference table (future postal directory dataset)
    op.create_table(
        'postal_locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pincode', sa.String(length=6), nullable=False),
        sa.Column('office_name', sa.String(length=150), nullable=False),
        sa.Column('office_type', sa.String(length=50), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('division', sa.String(length=100), nullable=True),
        sa.Column('delivery_status', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_postal_locations_id'), 'postal_locations', ['id'], unique=False)
    op.create_index(op.f('ix_postal_locations_pincode'), 'postal_locations', ['pincode'], unique=False)


def downgrade() -> None:
    op.drop_table('postal_locations')
    op.drop_table('delivery_otps')
    op.drop_table('parcel_qr_codes')
    op.drop_table('parcel_tracking_events')
    op.drop_index(op.f('ix_parcels_status'), table_name='parcels')
    op.drop_column('parcels', 'status')
