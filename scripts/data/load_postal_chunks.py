"""
Deterministic Postal Legal Document Chunks Loader.

Loads the 228 verified structure-aware legal chunks from Module 3 Step 2 into
the PostgreSQL database table 'postal_document_chunks'.

Enforces:
- Schema and JSONL validation
- Exactly 228 verified records
- Strict chunk ID uniqueness
- Non-empty statutory text
- Page provenance integrity (start_page <= end_page, source_pages match)
- Idempotent execution (skips/verifies if already populated without duplicate insertion)
- Post-load search_vector and GIN index verification
"""

import os
import sys
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List

# Ensure backend is in python path
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = WORKSPACE_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.postal_chunk import PostalDocumentChunk

SOURCE_CHUNKS_PATH = WORKSPACE_ROOT / "data" / "postal_documents" / "chunks" / "postal_english_chunks.jsonl"
EXPECTED_CHUNK_COUNT = 228


def validate_chunk_record(idx: int, chunk: Dict[str, Any]) -> None:
    required_fields = [
        "chunk_id", "document_id", "source_filename", "document_title",
        "document_type", "issuing_authority", "section_type", "heading",
        "start_page", "end_page", "source_pages", "legal_reference",
        "text", "char_count", "word_count", "language", "extraction_method",
        "source_version", "boundary_detection_method", "ocr_anomaly"
    ]
    for field in required_fields:
        if field not in chunk:
            raise ValueError(f"Record {idx} missing required field: '{field}'")
    
    # Non-empty text
    text_content = chunk["text"].strip()
    if not text_content:
        raise ValueError(f"Record {idx} ({chunk.get('chunk_id')}) has empty text content.")
    
    # Page provenance
    start_p = chunk["start_page"]
    end_p = chunk["end_page"]
    pages = chunk["source_pages"]
    if start_p > end_p:
        raise ValueError(f"Record {idx} ({chunk['chunk_id']}) has invalid page range: start_page ({start_p}) > end_page ({end_p})")
    if not isinstance(pages, list) or not pages:
        raise ValueError(f"Record {idx} ({chunk['chunk_id']}) has invalid source_pages: {pages}")
    if pages[0] != start_p or pages[-1] != end_p:
        raise ValueError(f"Record {idx} ({chunk['chunk_id']}) page provenance mismatch: pages {pages} vs {start_p}-{end_p}")


def load_and_validate_source_chunks() -> List[Dict[str, Any]]:
    if not SOURCE_CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Source chunks file not found: {SOURCE_CHUNKS_PATH}")
    
    chunks = []
    seen_chunk_ids = set()

    with open(SOURCE_CHUNKS_PATH, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
            except json.JSONDecodeError as err:
                raise ValueError(f"JSON syntax error on line {idx}: {err}")
            
            validate_chunk_record(idx, record)
            
            cid = record["chunk_id"]
            if cid in seen_chunk_ids:
                raise ValueError(f"Duplicate chunk_id detected on line {idx}: '{cid}'")
            seen_chunk_ids.add(cid)
            chunks.append(record)
    
    if len(chunks) != EXPECTED_CHUNK_COUNT:
        raise ValueError(
            f"Corpus count corruption: expected exactly {EXPECTED_CHUNK_COUNT} chunks, but found {len(chunks)}."
        )
    
    print(f" Source JSONL validated: {len(chunks)} structure-aware legal chunks loaded from {SOURCE_CHUNKS_PATH.name}")
    return chunks


def ingest_chunks_to_database(db_url: str = None) -> Dict[str, Any]:
    target_url = db_url or settings.DATABASE_URL
    print(f"Connecting to database: {target_url}")
    engine = create_engine(target_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Load and validate source records
        source_records = load_and_validate_source_chunks()

        # 2. Check existing count
        existing_count = session.scalar(select(func.count(PostalDocumentChunk.id))) or 0
        existing_chunk_ids = set(session.scalars(select(PostalDocumentChunk.chunk_id)).all())

        print(f" Current database state: {existing_count} chunks already in 'postal_document_chunks'")

        if existing_count == EXPECTED_CHUNK_COUNT and len(existing_chunk_ids) == EXPECTED_CHUNK_COUNT:
            # Check if all source chunk IDs are already present
            source_cids = set(r["chunk_id"] for r in source_records)
            if source_cids == existing_chunk_ids:
                print(f" IDEMPOTENCY CHECK PASSED: All {EXPECTED_CHUNK_COUNT} verified chunks are already loaded.")
                # Verify search_vector
                vector_populated = session.scalar(
                    select(func.count(PostalDocumentChunk.id)).where(PostalDocumentChunk.search_vector.isnot(None))
                ) or 0
                print(f" Search vector populated count: {vector_populated}/{EXPECTED_CHUNK_COUNT}")
                return {
                    "status": "ALREADY_LOADED",
                    "total_chunks": existing_count,
                    "search_vector_populated": vector_populated
                }

        # 3. Ingest missing chunks
        inserted_count = 0
        for r in source_records:
            cid = r["chunk_id"]
            if cid in existing_chunk_ids:
                continue

            pub_date = None
            if r.get("publication_date"):
                try:
                    pub_date = date.fromisoformat(r["publication_date"])
                except ValueError:
                    pub_date = None

            chunk_obj = PostalDocumentChunk(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                source_filename=r["source_filename"],
                document_title=r["document_title"],
                document_type=r["document_type"],
                issuing_authority=r["issuing_authority"],
                publication_date=pub_date,
                section_type=r["section_type"],
                unit_number=str(r["unit_number"]) if r.get("unit_number") is not None else None,
                heading=r["heading"],
                chapter_number=str(r["chapter_number"]) if r.get("chapter_number") is not None else None,
                chapter_title=r.get("chapter_title"),
                start_page=r["start_page"],
                end_page=r["end_page"],
                source_pages=r["source_pages"],
                legal_reference=r["legal_reference"],
                text=r["text"],
                char_count=r["char_count"],
                word_count=r["word_count"],
                language=r.get("language", "en"),
                extraction_method=r["extraction_method"],
                source_version=r.get("source_version", "1.0.0"),
                content_type=r.get("content_type", "legal_statute"),
                boundary_detection_method=r["boundary_detection_method"],
                ocr_anomaly=r.get("ocr_anomaly", False),
                anomaly_note=r.get("anomaly_note")
            )
            session.add(chunk_obj)
            inserted_count += 1

        session.commit()
        print(f" Successfully inserted {inserted_count} new chunks into 'postal_document_chunks'.")

        # 4. For PostgreSQL, if search_vector wasn't populated by trigger, populate it explicitly
        is_postgres = engine.dialect.name == "postgresql"
        if is_postgres:
            print(" Verifying and updating PostgreSQL tsvector column...")
            session.execute(text("""
                UPDATE postal_document_chunks
                SET search_vector = 
                    setweight(to_tsvector('english', coalesce(heading, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(legal_reference, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(text, '')), 'B')
                WHERE search_vector IS NULL;
            """))
            session.commit()

        # 5. Final integrity verification
        final_count = session.scalar(select(func.count(PostalDocumentChunk.id)))
        print(f"\n========================================================")
        print(f" DATABASE INGESTION INTEGRITY VERIFICATION")
        print(f"========================================================")
        print(f" Total Chunks in Database: {final_count} (Expected: {EXPECTED_CHUNK_COUNT})")
        assert final_count == EXPECTED_CHUNK_COUNT, f"Count mismatch: {final_count} != {EXPECTED_CHUNK_COUNT}"

        if is_postgres:
            null_vectors = session.scalar(
                select(func.count(PostalDocumentChunk.id)).where(PostalDocumentChunk.search_vector.is_(None))
            ) or 0
            print(f" NULL Search Vectors: {null_vectors} (Expected: 0)")
            assert null_vectors == 0, f"Found {null_vectors} unindexed chunks!"
            
            # Verify GIN index exists
            gin_check = session.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'postal_document_chunks' 
                  AND indexdef LIKE '%USING gin%';
            """)).fetchall()
            gin_names = [row[0] for row in gin_check]
            print(f" Active GIN Indexes on 'postal_document_chunks': {gin_names}")
            assert len(gin_names) > 0, "No GIN index found on postal_document_chunks!"

        print(" Ingestion and Index Verification 100% SUCCESSFUL.\n")
        return {
            "status": "SUCCESS",
            "total_chunks": final_count,
            "inserted": inserted_count
        }
    finally:
        session.close()


if __name__ == "__main__":
    ingest_chunks_to_database()
