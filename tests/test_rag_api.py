"""
Automated Test Suite for RAG API Endpoint.

Tests the POST /api/v1/postal/ask endpoint:
1. Valid request returns correct structure
2. Empty query rejected
3. Oversized query rejected
4. Invalid top_k rejected
5. Invalid retrieval_mode rejected
6. Response contains required fields
7. Insufficient evidence case via API
8. Mock provider works through API
9. Content-type validation
10. Multiple valid retrieval modes accepted
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.schemas.rag import RAGResponse


@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app) as c:
        yield c


def _mock_retrieval_response(results=None, mode="hybrid"):
    """Create a mock retrieval response."""
    return SimpleNamespace(
        query="test",
        total_matches=len(results or []),
        top_k=5,
        latency_ms=5.0,
        retrieval_mode=mode,
        results=results or [],
    )


def _mock_chunk():
    """Create a mock PostalChunkResult-like object."""
    return SimpleNamespace(
        chunk_id="DOC2_ACT_SECTION_09",
        legal_reference="Section 9",
        heading="Establishment of post offices",
        document_title="The Post Office Act, 2023",
        document_type="Act",
        section_type="section",
        start_page=13,
        end_page=13,
        source_pages=[13],
        relevance_score=0.85,
        text="The Central Government may establish post offices.",
        ocr_anomaly=False,
        anomaly_note=None,
        retrieval_mode="hybrid",
    )


class TestRAGAPIEndpoint:
    """Tests for POST /api/v1/postal/ask."""

    @patch("app.routes.postal.RAGSynthesisService")
    def test_valid_request(self, mock_service_class, client):
        """1. Valid request returns 200 with correct structure."""
        mock_instance = MagicMock()
        mock_instance.ask.return_value = RAGResponse(
            query="What is Section 9?",
            answer="Based on [1], the Central Government may establish post offices.",
            citations=[],
            retrieved_chunks=1,
            grounded=True,
            insufficient_evidence=False,
            retrieval_mode="hybrid",
        )
        mock_service_class.return_value = mock_instance

        response = client.post("/api/v1/postal/ask", json={
            "query": "What is Section 9?",
            "top_k": 5,
            "retrieval_mode": "hybrid",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["query"] == "What is Section 9?"
        assert data["data"]["grounded"] is True

    def test_empty_query_rejected(self, client):
        """2. Empty query string is rejected with 422."""
        response = client.post("/api/v1/postal/ask", json={
            "query": "",
            "top_k": 5,
            "retrieval_mode": "hybrid",
        })
        assert response.status_code == 422

    def test_missing_query_rejected(self, client):
        """3. Missing query field is rejected with 422."""
        response = client.post("/api/v1/postal/ask", json={
            "top_k": 5,
            "retrieval_mode": "hybrid",
        })
        assert response.status_code == 422

    def test_oversized_query_rejected(self, client):
        """4. Query exceeding max length is rejected."""
        response = client.post("/api/v1/postal/ask", json={
            "query": "x" * 1001,
            "top_k": 5,
            "retrieval_mode": "hybrid",
        })
        assert response.status_code == 422

    def test_invalid_top_k_too_low(self, client):
        """5. top_k=0 is rejected."""
        response = client.post("/api/v1/postal/ask", json={
            "query": "Test question",
            "top_k": 0,
            "retrieval_mode": "hybrid",
        })
        assert response.status_code == 422

    def test_invalid_top_k_too_high(self, client):
        """6. top_k=100 is rejected."""
        response = client.post("/api/v1/postal/ask", json={
            "query": "Test question",
            "top_k": 100,
            "retrieval_mode": "hybrid",
        })
        assert response.status_code == 422

    def test_invalid_retrieval_mode(self, client):
        """7. Invalid retrieval_mode is rejected with 400."""
        response = client.post("/api/v1/postal/ask", json={
            "query": "Test question",
            "top_k": 5,
            "retrieval_mode": "invalid_mode",
        })
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "INVALID_RETRIEVAL_MODE" in data["error"]["code"]

    @patch("app.routes.postal.RAGSynthesisService")
    def test_insufficient_evidence_response(self, mock_service_class, client):
        """8. Insufficient evidence returns proper structure."""
        mock_instance = MagicMock()
        mock_instance.ask.return_value = RAGResponse(
            query="Unrelated query",
            answer="I could not find sufficient information...",
            citations=[],
            retrieved_chunks=0,
            grounded=False,
            insufficient_evidence=True,
            retrieval_mode="hybrid",
        )
        mock_service_class.return_value = mock_instance

        response = client.post("/api/v1/postal/ask", json={
            "query": "Unrelated query",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["insufficient_evidence"] is True
        assert data["data"]["grounded"] is False

    @patch("app.routes.postal.RAGSynthesisService")
    def test_response_contains_all_fields(self, mock_service_class, client):
        """9. Response data contains all required RAGResponse fields."""
        from app.schemas.rag import CitationDetail
        mock_instance = MagicMock()
        mock_instance.ask.return_value = RAGResponse(
            query="What is Section 9?",
            answer="Answer text [1]",
            citations=[CitationDetail(
                citation_id=1,
                document_id="DOC2",
                document_title="The Post Office Act, 2023",
                chunk_id="DOC2_ACT_SECTION_09",
                page=13,
                source_pages=[13],
                legal_reference="Section 9",
                extracted_text="Some extracted postal text.",
                retrieval_score=0.9,
                retrieval_mode="hybrid"
            )],
            retrieved_chunks=1,
            grounded=True,
            insufficient_evidence=False,
            retrieval_mode="hybrid",
            has_invalid_citations=False,
            invalid_citation_ids=[],
        )
        mock_service_class.return_value = mock_instance

        response = client.post("/api/v1/postal/ask", json={
            "query": "What is Section 9?",
        })
        data = response.json()["data"]

        assert "query" in data
        assert "answer" in data
        assert "citations" in data
        assert "retrieved_chunks" in data
        assert "grounded" in data
        assert "insufficient_evidence" in data
        assert "retrieval_mode" in data
        assert len(data["citations"]) == 1
        assert data["citations"][0]["document_id"] == "DOC2"
        assert "extracted_text" in data["citations"][0]
        assert data["citations"][0]["extracted_text"] == "Some extracted postal text."

    @patch("app.routes.postal.RAGSynthesisService")
    def test_llm_provider_error_returns_503(self, mock_service_class, client):
        """10. LLM provider error returns 503 Service Unavailable."""
        from app.services.llm_provider import LLMProviderError
        mock_instance = MagicMock()
        mock_instance.ask.side_effect = LLMProviderError("API key invalid")
        mock_service_class.return_value = mock_instance

        response = client.post("/api/v1/postal/ask", json={
            "query": "Test question",
        })
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert "LLM_PROVIDER_ERROR" in data["error"]["code"]

    @patch("app.routes.postal.RAGSynthesisService")
    def test_valid_modes_accepted(self, mock_service_class, client):
        """11. All valid retrieval modes are accepted."""
        mock_instance = MagicMock()
        mock_instance.ask.return_value = RAGResponse(
            query="Test",
            answer="Answer",
            citations=[],
            retrieved_chunks=1,
            grounded=True,
            insufficient_evidence=False,
            retrieval_mode="hybrid",
        )
        mock_service_class.return_value = mock_instance

        for mode in ["hybrid", "lexical", "dense"]:
            response = client.post("/api/v1/postal/ask", json={
                "query": "Test question",
                "retrieval_mode": mode,
            })
            assert response.status_code == 200, f"Mode '{mode}' should be accepted"

    def test_default_values_applied(self, client):
        """12. Default top_k and retrieval_mode are applied when not specified."""
        # This validates the schema defaults work — the request is valid
        # even without explicit top_k and retrieval_mode
        with patch("app.routes.postal.RAGSynthesisService") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.ask.return_value = RAGResponse(
                query="Test",
                answer="Answer",
                citations=[],
                retrieved_chunks=1,
                grounded=True,
                insufficient_evidence=False,
                retrieval_mode="hybrid",
            )
            mock_cls.return_value = mock_instance

            response = client.post("/api/v1/postal/ask", json={
                "query": "What is the Post Office Act?",
            })
            assert response.status_code == 200
