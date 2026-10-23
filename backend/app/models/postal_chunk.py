"""
SQLAlchemy Model for Structure-Aware Postal Document Chunks.

Stores the 228 verified legal/statutory chunks produced by Module 3 Step 2.
Supports PostgreSQL native full-text search (tsvector + GIN) while maintaining
cross-dialect fallback for local development and existing SQLite test suites.
"""

from sqlalchemy import Column, Integer, String, Text, Date, Boolean, JSON
from sqlalchemy.dialects.postgresql import TSVECTOR, ARRAY
from app.database.base import Base


class PostalDocumentChunk(Base):
    __tablename__ = "postal_document_chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chunk_id = Column(String(50), unique=True, nullable=False, index=True)
    document_id = Column(String(30), nullable=False, index=True)
    source_filename = Column(String(255), nullable=False)
    document_title = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False, index=True)
    issuing_authority = Column(String(255), nullable=False)
    publication_date = Column(Date, nullable=True)
    section_type = Column(String(50), nullable=False, index=True)
    unit_number = Column(String(50), nullable=True)
    heading = Column(Text, nullable=False)
    chapter_number = Column(String(20), nullable=True)
    chapter_title = Column(Text, nullable=True)
    start_page = Column(Integer, nullable=False)
    end_page = Column(Integer, nullable=False)
    source_pages = Column(JSON().with_variant(ARRAY(Integer), "postgresql"), nullable=False)
    legal_reference = Column(String(255), nullable=False, index=True)
    text = Column(Text, nullable=False)
    char_count = Column(Integer, nullable=False)
    word_count = Column(Integer, nullable=False)
    language = Column(String(20), nullable=False, default="en")
    extraction_method = Column(String(50), nullable=False)
    source_version = Column(String(50), nullable=False, default="1.0.0")
    content_type = Column(String(50), nullable=False, default="legal_statute")
    boundary_detection_method = Column(String(50), nullable=False)
    ocr_anomaly = Column(Boolean, nullable=False, default=False)
    anomaly_note = Column(Text, nullable=True)
    search_vector = Column(Text().with_variant(TSVECTOR, "postgresql"), nullable=True)

    def __repr__(self) -> str:
        return f"<PostalDocumentChunk(chunk_id='{self.chunk_id}', ref='{self.legal_reference}')>"
