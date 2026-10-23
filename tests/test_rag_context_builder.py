"""
Automated Test Suite for RAG Context Builder.

Tests the deterministic context construction from retrieved postal chunks:
1. deterministic ordering by retrieval rank
2. metadata preservation (chunk_id, document_id, legal_reference)
3. page preservation (start_page, source_pages)
4. chunk_id preservation in source map
5. no fabricated metadata
6. document_id extraction
7. empty input handling
8. XML structure correctness
9. source map citation_id mapping
10. multiple chunks produce correct ordering
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.rag_context_builder import RAGContextBuilder


def _make_chunk_result(**overrides):
    """Create a mock PostalChunkResult-like object for testing."""
    defaults = {
        "chunk_id": "DOC1_RULE_05",
        "legal_reference": "Post Office Rules, 2024 — Rule 5",
        "heading": "Postal Services Board",
        "document_title": "Post Office Rules, 2024",
        "document_type": "Rules",
        "section_type": "rule",
        "start_page": 7,
        "end_page": 7,
        "source_pages": [7],
        "relevance_score": 0.85,
        "text": "The Board shall consist of a Chairperson and Members.",
        "ocr_anomaly": False,
        "anomaly_note": None,
        "lexical_rank": 1,
        "dense_rank": 2,
        "lexical_score": 0.9,
        "dense_similarity": 0.82,
        "retrieval_mode": "hybrid",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestRAGContextBuilder:
    """Tests for RAGContextBuilder."""

    def setup_method(self):
        self.builder = RAGContextBuilder()

    def test_empty_input_returns_empty(self):
        """1. Empty list of results produces empty context and empty source map."""
        context, source_map = self.builder.build_context([])
        assert context == ""
        assert source_map == {}

    def test_single_chunk_produces_valid_context(self):
        """2. Single chunk produces a well-formed XML-tagged context block."""
        chunk = _make_chunk_result()
        context, source_map = self.builder.build_context([chunk])

        assert '<OFFICIAL_POSTAL_SOURCE id="1">' in context
        assert "</OFFICIAL_POSTAL_SOURCE>" in context
        assert "Document ID: DOC1" in context
        assert "Post Office Rules, 2024" in context
        assert "Rule 5" in context
        assert "Page: 7" in context
        assert len(source_map) == 1
        assert 1 in source_map

    def test_metadata_preservation_chunk_id(self):
        """3. chunk_id is preserved in the source map."""
        chunk = _make_chunk_result(chunk_id="DOC2_REG_048")
        _, source_map = self.builder.build_context([chunk])
        assert source_map[1]["chunk_id"] == "DOC2_REG_048"

    def test_metadata_preservation_document_id(self):
        """4. document_id is correctly extracted and stored."""
        chunk = _make_chunk_result(chunk_id="DOC2_ACT_SECTION_09")
        _, source_map = self.builder.build_context([chunk])
        assert source_map[1]["document_id"] == "DOC2"

    def test_metadata_preservation_legal_reference(self):
        """5. legal_reference is preserved from the retrieval result."""
        ref = "Post Office Act, 2023 — Section 9"
        chunk = _make_chunk_result(legal_reference=ref)
        _, source_map = self.builder.build_context([chunk])
        assert source_map[1]["legal_reference"] == ref

    def test_page_preservation(self):
        """6. start_page and source_pages are preserved."""
        chunk = _make_chunk_result(start_page=13, source_pages=[13, 14])
        _, source_map = self.builder.build_context([chunk])
        assert source_map[1]["page"] == 13
        assert source_map[1]["source_pages"] == [13, 14]

    def test_page_in_context_string(self):
        """7. Page number appears in the formatted context string."""
        chunk = _make_chunk_result(start_page=42, source_pages=[42, 43])
        context, _ = self.builder.build_context([chunk])
        assert "Page: 42" in context
        assert "Source Pages: 42, 43" in context

    def test_deterministic_ordering_multiple_chunks(self):
        """8. Multiple chunks maintain retrieval order (1, 2, 3...)."""
        chunks = [
            _make_chunk_result(chunk_id="DOC1_RULE_01", relevance_score=0.9, text="First chunk"),
            _make_chunk_result(chunk_id="DOC2_REG_048", relevance_score=0.7, text="Second chunk"),
            _make_chunk_result(chunk_id="DOC2_ACT_SECTION_09", relevance_score=0.5, text="Third chunk"),
        ]
        context, source_map = self.builder.build_context(chunks)

        assert len(source_map) == 3
        assert source_map[1]["chunk_id"] == "DOC1_RULE_01"
        assert source_map[2]["chunk_id"] == "DOC2_REG_048"
        assert source_map[3]["chunk_id"] == "DOC2_ACT_SECTION_09"

        # Verify ordering in context string
        pos1 = context.index('id="1"')
        pos2 = context.index('id="2"')
        pos3 = context.index('id="3"')
        assert pos1 < pos2 < pos3

    def test_no_fabricated_metadata(self):
        """9. Source map only contains data from the actual retrieved result."""
        chunk = _make_chunk_result(
            chunk_id="DOC1_RULE_03",
            document_title="Post Office Rules, 2024",
            legal_reference="Rule 3",
            start_page=6,
            source_pages=[6],
        )
        _, source_map = self.builder.build_context([chunk])
        entry = source_map[1]

        # Verify all fields come from the chunk
        assert entry["chunk_id"] == "DOC1_RULE_03"
        assert entry["document_id"] == "DOC1"
        assert entry["document_title"] == "Post Office Rules, 2024"
        assert entry["legal_reference"] == "Rule 3"
        assert entry["page"] == 6
        assert entry["source_pages"] == [6]
        assert entry["retrieval_rank"] == 1

    def test_document_id_extraction_doc1(self):
        """10. DOC1 prefix extracted correctly."""
        assert self.builder._extract_document_id("DOC1_RULE_02") == "DOC1"

    def test_document_id_extraction_doc2(self):
        """11. DOC2 prefix extracted correctly."""
        assert self.builder._extract_document_id("DOC2_ACT_SECTION_09") == "DOC2"

    def test_document_id_extraction_unknown(self):
        """12. Non-standard chunk_id returns UNKNOWN."""
        assert self.builder._extract_document_id("INVALID_CHUNK") == "UNKNOWN"

    def test_document_id_extraction_empty(self):
        """13. Empty chunk_id returns UNKNOWN."""
        assert self.builder._extract_document_id("") == "UNKNOWN"

    def test_text_preserved_in_context(self):
        """14. The full text of the retrieved chunk appears in the context."""
        test_text = "This is the actual legal text of the section."
        chunk = _make_chunk_result(text=test_text)
        context, _ = self.builder.build_context([chunk])
        assert test_text in context

    def test_relevance_score_in_source_map(self):
        """15. Relevance score is preserved as a float in the source map."""
        chunk = _make_chunk_result(relevance_score=0.03245)
        _, source_map = self.builder.build_context([chunk])
        assert source_map[1]["relevance_score"] == 0.03245

    def test_source_pages_non_list_handled(self):
        """16. Non-list source_pages fallback to [start_page]."""
        chunk = _make_chunk_result(start_page=10, source_pages=None)
        _, source_map = self.builder.build_context([chunk])
        assert source_map[1]["source_pages"] == [10]
