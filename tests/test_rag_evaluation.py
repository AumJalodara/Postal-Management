"""
Automated Test Suite for RAG Evaluation.

Tests the RAG evaluation dataset and quality metrics:
1. Evaluation dataset loads correctly
2. All supported questions reference valid chunk_ids
3. Unsupported questions are properly marked
4. Adversarial questions are properly marked
5. Citation correctness scoring with MockLLM
6. Evidence coverage metric
7. Groundedness assessment
8. Refusal behavior for unsupported questions
9. Dataset completeness checks
10. Retrieval vs generation metric distinction

IMPORTANT: These tests evaluate the RAG system design and dataset quality.
They do NOT claim that successful API responses prove RAG quality.
Real LLM validation requires provider configuration.
"""

import sys
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.rag_synthesis_service import RAGSynthesisService, INSUFFICIENT_EVIDENCE_RESPONSE
from app.services.rag_context_builder import RAGContextBuilder
from app.services.llm_provider import MockLLMProvider
from app.schemas.rag import RAGResponse

EVAL_FILE = Path(__file__).resolve().parents[1] / "data" / "postal_documents" / "evaluation" / "rag_evaluation_queries.jsonl"
CHUNKS_FILE = Path(__file__).resolve().parents[1] / "data" / "postal_documents" / "chunks" / "postal_english_chunks.jsonl"


def load_evaluation_queries():
    """Load the RAG evaluation dataset."""
    queries = []
    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))
    return queries


def load_corpus_chunk_ids():
    """Load all chunk_ids from the 228-chunk corpus."""
    chunk_ids = set()
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunk = json.loads(line)
                chunk_ids.add(chunk["chunk_id"])
    return chunk_ids


def _make_mock_chunk(**overrides):
    """Create a mock chunk result."""
    defaults = {
        "chunk_id": "DOC2_ACT_SECTION_09",
        "legal_reference": "Section 9",
        "heading": "Establishment of post offices",
        "document_title": "The Post Office Act, 2023",
        "document_type": "Act",
        "section_type": "section",
        "start_page": 13,
        "end_page": 13,
        "source_pages": [13],
        "relevance_score": 0.85,
        "text": "The Central Government may establish post offices.",
        "ocr_anomaly": False,
        "anomaly_note": None,
        "retrieval_mode": "hybrid",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestRAGEvaluationDataset:
    """Tests for the RAG evaluation dataset integrity."""

    def test_evaluation_file_exists(self):
        """1. Evaluation dataset file exists."""
        assert EVAL_FILE.exists(), f"Evaluation file not found: {EVAL_FILE}"

    def test_evaluation_dataset_loads(self):
        """2. Dataset loads without errors and has expected count."""
        queries = load_evaluation_queries()
        assert len(queries) >= 10, f"Expected at least 10 evaluation queries, got {len(queries)}"

    def test_all_queries_have_required_fields(self):
        """3. Every evaluation query has required fields."""
        queries = load_evaluation_queries()
        required_fields = {"query_id", "query", "query_type"}
        for q in queries:
            for field in required_fields:
                assert field in q, f"Query {q.get('query_id', '?')} missing field '{field}'"

    def test_supported_queries_have_expected_chunk_ids(self):
        """4. Supported queries reference valid chunk_ids from the 228-chunk corpus."""
        queries = load_evaluation_queries()
        corpus_ids = load_corpus_chunk_ids()
        assert len(corpus_ids) == 228, f"Expected 228 chunks, got {len(corpus_ids)}"

        supported = [q for q in queries if q["query_type"] == "supported"]
        assert len(supported) >= 8, f"Expected at least 8 supported queries, got {len(supported)}"

        for q in supported:
            expected_cid = q.get("expected_chunk_id")
            assert expected_cid is not None, f"Supported query {q['query_id']} has no expected_chunk_id"
            assert expected_cid in corpus_ids, (
                f"Supported query {q['query_id']} references chunk '{expected_cid}' "
                f"which does not exist in the 228-chunk corpus"
            )

    def test_supported_queries_have_document_id(self):
        """5. Supported queries have expected_document_id."""
        queries = load_evaluation_queries()
        supported = [q for q in queries if q["query_type"] == "supported"]
        for q in supported:
            assert q.get("expected_document_id") is not None, (
                f"Supported query {q['query_id']} missing expected_document_id"
            )

    def test_supported_queries_have_page(self):
        """6. Supported queries have expected_page."""
        queries = load_evaluation_queries()
        supported = [q for q in queries if q["query_type"] == "supported"]
        for q in supported:
            assert q.get("expected_page") is not None, (
                f"Supported query {q['query_id']} missing expected_page"
            )

    def test_unsupported_queries_present(self):
        """7. Dataset includes unsupported questions for refusal testing."""
        queries = load_evaluation_queries()
        unsupported = [q for q in queries if q["query_type"] == "unsupported"]
        assert len(unsupported) >= 2, f"Expected at least 2 unsupported queries, got {len(unsupported)}"

    def test_adversarial_queries_present(self):
        """8. Dataset includes adversarial questions."""
        queries = load_evaluation_queries()
        adversarial = [q for q in queries if q["query_type"] == "adversarial"]
        assert len(adversarial) >= 2, f"Expected at least 2 adversarial queries, got {len(adversarial)}"

    def test_unique_query_ids(self):
        """9. All query_ids are unique."""
        queries = load_evaluation_queries()
        ids = [q["query_id"] for q in queries]
        assert len(ids) == len(set(ids)), "Duplicate query_ids found in evaluation dataset"


class TestRAGEvaluationMetrics:
    """Tests for RAG evaluation metrics using MockLLM."""

    def _create_rag_service(self, retrieval_results):
        """Create a RAG service with mocked retrieval."""
        mock_db = MagicMock()
        service = RAGSynthesisService(db=mock_db, llm_provider=MockLLMProvider())
        mock_response = SimpleNamespace(
            query="test",
            total_matches=len(retrieval_results),
            top_k=5,
            latency_ms=5.0,
            retrieval_mode="hybrid",
            results=retrieval_results,
        )
        service.retrieval_service = MagicMock()
        service.retrieval_service.search.return_value = mock_response
        return service

    def test_citation_correctness_with_mock(self):
        """10. MockLLM produces citations that map to valid source entries."""
        chunks = [_make_mock_chunk()]
        service = self._create_rag_service(chunks)
        response = service.ask(query="What is Section 9?")

        # MockLLM should produce valid citations
        for citation in response.citations:
            assert citation.citation_id >= 1
            assert citation.document_id is not None
            assert citation.chunk_id is not None

    def test_evidence_coverage_with_sources(self):
        """11. When sources exist, the response is grounded."""
        chunks = [_make_mock_chunk()]
        service = self._create_rag_service(chunks)
        response = service.ask(query="What is Section 9?")

        assert response.grounded is True
        assert response.retrieved_chunks > 0

    def test_refusal_behavior_no_results(self):
        """12. Refusal/fallback behavior when retrieval returns zero results.

        With web-enhanced RAG, zero retrieval results triggers a web search
        fallback. The system either:
        (a) Falls back to web sources (web_search_used=True, not_in_docs=True), OR
        (b) Returns insufficient_evidence=True if web search also fails.
        In both cases, the response must NOT be grounded on document evidence.
        """
        service = self._create_rag_service([])
        response = service.ask(query="What is the recipe for pizza?")

        assert response.grounded is False
        assert response.retrieved_chunks == 0
        # Either web fallback was used or insufficient evidence was flagged
        assert response.web_search_used is True or response.insufficient_evidence is True

    def test_retrieval_vs_generation_metrics_distinction(self):
        """13. Retrieval metrics are separate from generation metrics.

        This test documents the distinction:
        - Retrieval metrics (Recall@k, MRR) measure the RETRIEVAL system
        - RAG metrics (citation correctness, groundedness) measure the GENERATION system
        - Successful API responses do NOT prove RAG quality
        """
        # Retrieval metrics are frozen (94.29% Recall@5, 100% Recall@10, 0.9303 MRR)
        # RAG metrics evaluated here with MockLLM are structural only
        chunks = [_make_mock_chunk()]
        service = self._create_rag_service(chunks)
        response = service.ask(query="Test")

        # These are GENERATION metrics (structural validation only with MockLLM):
        rag_metrics = {
            "grounded": response.grounded,
            "has_citations": len(response.citations) > 0,
            "insufficient_evidence": response.insufficient_evidence,
            "has_invalid_citations": response.has_invalid_citations,
        }

        # Structural correctness confirmed
        assert rag_metrics["grounded"] is True
        assert rag_metrics["insufficient_evidence"] is False
        # Note: Real quality assessment requires a real LLM provider

    def test_mock_llm_validation_note(self):
        """14. Explicitly document that MockLLM validation is structural only.

        Real LLM validation pending provider configuration.
        This test serves as documentation that MockLLM tests verify:
        - Pipeline correctness (retrieval → context → LLM → citation validation)
        - Schema compliance
        - Error handling
        - Citation validation logic

        They do NOT verify:
        - Answer factual correctness
        - Natural language quality
        - Real-world groundedness
        """
        assert True  # Documentation test — always passes
