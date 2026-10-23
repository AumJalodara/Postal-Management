"""module 3 postal document chunks migration

Revision ID: 003_module3_postal_chunks
Revises: 002_module2_tracking_qr_otp
Create Date: 2026-09-11 23:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '003_module3_postal_chunks'
down_revision: Union[str, None] = '002_module2_tracking_qr_otp'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # 1. Create table postal_document_chunks
    op.create_table(
        'postal_document_chunks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chunk_id', sa.String(length=50), nullable=False),
        sa.Column('document_id', sa.String(length=30), nullable=False),
        sa.Column('source_filename', sa.String(length=255), nullable=False),
        sa.Column('document_title', sa.String(length=255), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('issuing_authority', sa.String(length=255), nullable=False),
        sa.Column('publication_date', sa.Date(), nullable=True),
        sa.Column('section_type', sa.String(length=50), nullable=False),
        sa.Column('unit_number', sa.String(length=50), nullable=True),
        sa.Column('heading', sa.Text(), nullable=False),
        sa.Column('chapter_number', sa.String(length=20), nullable=True),
        sa.Column('chapter_title', sa.Text(), nullable=True),
        sa.Column('start_page', sa.Integer(), nullable=False),
        sa.Column('end_page', sa.Integer(), nullable=False),
        sa.Column('source_pages', postgresql.ARRAY(sa.Integer()) if is_postgres else sa.JSON(), nullable=False),
        sa.Column('legal_reference', sa.String(length=255), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('char_count', sa.Integer(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=20), server_default='en', nullable=False),
        sa.Column('extraction_method', sa.String(length=50), nullable=False),
        sa.Column('source_version', sa.String(length=50), server_default='1.0.0', nullable=False),
        sa.Column('content_type', sa.String(length=50), server_default='legal_statute', nullable=False),
        sa.Column('boundary_detection_method', sa.String(length=50), nullable=False),
        sa.Column('ocr_anomaly', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('anomaly_note', sa.Text(), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR() if is_postgres else sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chunk_id')
    )

    op.create_index(op.f('ix_postal_document_chunks_id'), 'postal_document_chunks', ['id'], unique=False)
    op.create_index(op.f('ix_postal_document_chunks_chunk_id'), 'postal_document_chunks', ['chunk_id'], unique=True)
    op.create_index(op.f('ix_postal_document_chunks_document_id'), 'postal_document_chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_postal_document_chunks_document_type'), 'postal_document_chunks', ['document_type'], unique=False)
    op.create_index(op.f('ix_postal_document_chunks_section_type'), 'postal_document_chunks', ['section_type'], unique=False)
    op.create_index(op.f('ix_postal_document_chunks_legal_reference'), 'postal_document_chunks', ['legal_reference'], unique=False)

    # 2. PostgreSQL-specific full-text search: GIN Index & Trigger
    if is_postgres:
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_postal_document_chunks_search_vector "
            "ON postal_document_chunks USING GIN(search_vector);"
        )
        op.execute("""
            CREATE OR REPLACE FUNCTION postal_chunks_tsvector_trigger() RETURNS trigger AS $$
            BEGIN
                NEW.search_vector := 
                    setweight(to_tsvector('english', coalesce(NEW.heading, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(NEW.legal_reference, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(NEW.text, '')), 'B');
                RETURN NEW;
            END
            $$ LANGUAGE plpgsql;
        """)
        op.execute("""
            DROP TRIGGER IF EXISTS trg_postal_chunks_tsvector_update ON postal_document_chunks;
            CREATE TRIGGER trg_postal_chunks_tsvector_update
            BEFORE INSERT OR UPDATE ON postal_document_chunks
            FOR EACH ROW EXECUTE FUNCTION postal_chunks_tsvector_trigger();
        """)


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    if is_postgres:
        op.execute("DROP TRIGGER IF EXISTS trg_postal_chunks_tsvector_update ON postal_document_chunks;")
        op.execute("DROP FUNCTION IF EXISTS postal_chunks_tsvector_trigger();")
        op.execute("DROP INDEX IF EXISTS ix_postal_document_chunks_search_vector;")

    op.drop_index(op.f('ix_postal_document_chunks_legal_reference'), table_name='postal_document_chunks')
    op.drop_index(op.f('ix_postal_document_chunks_section_type'), table_name='postal_document_chunks')
    op.drop_index(op.f('ix_postal_document_chunks_document_type'), table_name='postal_document_chunks')
    op.drop_index(op.f('ix_postal_document_chunks_document_id'), table_name='postal_document_chunks')
    op.drop_index(op.f('ix_postal_document_chunks_chunk_id'), table_name='postal_document_chunks')
    op.drop_index(op.f('ix_postal_document_chunks_id'), table_name='postal_document_chunks')
    op.drop_table('postal_document_chunks')
