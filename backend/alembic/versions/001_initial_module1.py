"""initial module 1 migration

Revision ID: 001_initial_module1
Revises: 
Create Date: 2026-09-06 22:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_module1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # Create sequence for tracking IDs in PostgreSQL
    if is_postgres:
        op.execute("CREATE SEQUENCE IF NOT EXISTS postal_tracking_seq START WITH 1 INCREMENT BY 1;")

    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=15), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('CITIZEN', 'AGENT', 'ADMIN', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Delivery Agents table
    op.create_table(
        'delivery_agents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('service_area', sa.String(length=50), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('active_pickup_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_delivery_agents_id'), 'delivery_agents', ['id'], unique=False)
    op.create_index(op.f('ix_delivery_agents_service_area'), 'delivery_agents', ['service_area'], unique=False)
    op.create_index(op.f('ix_delivery_agents_is_available'), 'delivery_agents', ['is_available'], unique=False)

    # Parcels table
    op.create_table(
        'parcels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tracking_id', sa.String(length=30), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('receiver_name', sa.String(length=100), nullable=False),
        sa.Column('receiver_phone', sa.String(length=15), nullable=False),
        sa.Column('destination_address', sa.String(length=300), nullable=False),
        sa.Column('destination_city', sa.String(length=100), nullable=False),
        sa.Column('destination_state', sa.String(length=100), nullable=False),
        sa.Column('destination_pin', sa.String(length=6), nullable=False),
        sa.Column('weight', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('parcel_type', sa.Enum('DOCUMENT', 'SMALL_PARCEL', 'MEDIUM_PARCEL', 'LARGE_PARCEL', name='parceltype'), nullable=False),
        sa.Column('priority', sa.Enum('STANDARD', 'EXPRESS', name='priority'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('weight > 0 AND weight <= 50', name='check_parcel_weight_range'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_parcels_id'), 'parcels', ['id'], unique=False)
    op.create_index(op.f('ix_parcels_tracking_id'), 'parcels', ['tracking_id'], unique=True)
    op.create_index(op.f('ix_parcels_sender_id'), 'parcels', ['sender_id'], unique=False)
    op.create_index(op.f('ix_parcels_destination_pin'), 'parcels', ['destination_pin'], unique=False)

    # Pickup Requests table
    op.create_table(
        'pickup_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parcel_id', sa.Integer(), nullable=False),
        sa.Column('requester_id', sa.Integer(), nullable=False),
        sa.Column('pickup_address', sa.String(length=300), nullable=False),
        sa.Column('pickup_city', sa.String(length=100), nullable=False),
        sa.Column('pickup_state', sa.String(length=100), nullable=False),
        sa.Column('pickup_pin', sa.String(length=6), nullable=False),
        sa.Column('requested_date', sa.Date(), nullable=False),
        sa.Column('assigned_agent_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'ASSIGNED', 'ACCEPTED', 'PICKED_UP', 'CANCELLED', name='pickupstatus'), nullable=False),
        sa.Column('idempotency_key', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_agent_id'], ['delivery_agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parcel_id'], ['parcels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('parcel_id')
    )
    op.create_index(op.f('ix_pickup_requests_id'), 'pickup_requests', ['id'], unique=False)
    op.create_index(op.f('ix_pickup_requests_requester_id'), 'pickup_requests', ['requester_id'], unique=False)
    op.create_index(op.f('ix_pickup_requests_assigned_agent_id'), 'pickup_requests', ['assigned_agent_id'], unique=False)
    op.create_index(op.f('ix_pickup_requests_pickup_pin'), 'pickup_requests', ['pickup_pin'], unique=False)
    op.create_index(op.f('ix_pickup_requests_status'), 'pickup_requests', ['status'], unique=False)
    op.create_index(op.f('ix_pickup_requests_idempotency_key'), 'pickup_requests', ['idempotency_key'], unique=True)

    # Pickup Status History table
    op.create_table(
        'pickup_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pickup_id', sa.Integer(), nullable=False),
        sa.Column('old_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('changed_by_role', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['pickup_id'], ['pickup_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pickup_status_history_id'), 'pickup_status_history', ['id'], unique=False)
    op.create_index(op.f('ix_pickup_status_history_pickup_id'), 'pickup_status_history', ['pickup_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    op.drop_table('pickup_status_history')
    op.drop_table('pickup_requests')
    op.drop_table('parcels')
    op.drop_table('delivery_agents')
    op.drop_table('users')

    if is_postgres:
        op.execute("DROP SEQUENCE IF EXISTS postal_tracking_seq;")
        op.execute("DROP TYPE IF EXISTS userrole;")
        op.execute("DROP TYPE IF EXISTS parceltype;")
        op.execute("DROP TYPE IF EXISTS priority;")
        op.execute("DROP TYPE IF EXISTS pickupstatus;")
