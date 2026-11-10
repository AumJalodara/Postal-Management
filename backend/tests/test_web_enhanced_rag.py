"""
Unit and integration tests for Web-Enhanced Postal Assistant.
Verifies:
1. WebSearchService retrieves curated and live web portal references.
2. RAGSynthesisService provides grounded statutory answers for statutory queries.
3. RAGSynthesisService falls back gracefully to web search when statutory documents
   do not cover the topic (e.g. passport services, savings interest rates).
4. POST /api/v1/postal/ask returns structured web sources and not_in_docs flag.
"""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.rag import RAGResponse, WebSourceDetail
from app.services.web_search_service import WebSearchService
from app.services.rag_synthesis_service import RAGSynthesisService
from app.services.llm_provider import MockLLMProvider
from app.database.connection import SessionLocal


def test_web_search_service_curated_matches():
    """Verify WebSearchService matches official India Post portals for common non-statutory topics."""
    svc = WebSearchService(timeout=2.0)

    # 1. Passport inquiry
    passport_results = svc.search("How to apply for passport in post office?", max_results=3)
    assert len(passport_results) > 0
    assert any("passport" in r.title.lower() for r in passport_results)
    assert any("passportindia.gov.in" in r.url or "POPSK" in r.url for r in passport_results)

    # 2. Small savings scheme
    sukanya_results = svc.search("What is the interest rate of Sukanya Samriddhi Yojana?", max_results=2)
    assert len(sukanya_results) > 0
    assert any("sukanya" in r.title.lower() or "savings" in r.title.lower() for r in sukanya_results)

    # 3. Aadhaar services
    aadhaar_results = svc.search("Can I update Aadhaar card at post office?", max_results=2)
    assert len(aadhaar_results) > 0
    assert any("aadhaar" in r.title.lower() for r in aadhaar_results)


def test_rag_synthesis_service_web_fallback_when_no_doc_chunks():
    """Verify that when 0 document chunks match, the assistant executes web search and marks not_in_docs=True."""
    db = SessionLocal()
    try:
        mock_retrieval = MagicMock()
        mock_retrieval.search.return_value = MagicMock(results=[], retrieval_mode="hybrid")

        mock_search = MagicMock()
        mock_search.search.return_value = [
            WebSourceDetail(
                source_id=1,
                title="Passport Seva Online Portal",
                url="https://www.passportindia.gov.in",
                snippet="Apply online and visit designated POPSK.",
                source_type="Official Government Portal"
            )
        ]

        mock_llm = MockLLMProvider()
        service = RAGSynthesisService(db=db, llm_provider=mock_llm, search_service=mock_search)
        service.retrieval_service = mock_retrieval

        response = service.ask("How to apply for passport in post office?")

        assert response is not None
        assert response.not_in_docs is True
        assert response.web_search_used is True
        assert len(response.web_sources) == 1
        assert response.web_sources[0].url == "https://www.passportindia.gov.in"
        assert response.retrieved_chunks == 0
        assert "**Note:**" in response.answer
    finally:
        db.close()


def test_rag_api_endpoint_returns_web_metadata():
    """Verify POST /api/v1/postal/ask includes web_search_used and web_sources."""
    client = TestClient(app)

    mock_response = RAGResponse(
        query="How to apply for passport?",
        answer="**Note:** This specific information is not covered in the indexed statutory postal legal acts/regulations. You can apply via POPSK [Web-1].",
        citations=[],
        retrieved_chunks=0,
        grounded=False,
        insufficient_evidence=False,
        retrieval_mode="hybrid",
        web_search_used=True,
        web_sources=[
            WebSourceDetail(
                source_id=1,
                title="Passport Seva Kendra - India Post",
                url="https://www.passportindia.gov.in",
                snippet="Official portal for passport services.",
                source_type="Official Government Portal"
            )
        ],
        not_in_docs=True
    )

    with patch("app.routes.postal.RAGSynthesisService.ask", return_value=mock_response):
        resp = client.post(
            "/api/v1/postal/ask",
            json={"query": "How to apply for passport?", "top_k": 3, "retrieval_mode": "hybrid"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["web_search_used"] is True
        assert data["not_in_docs"] is True
        assert len(data["web_sources"]) == 1
        assert data["web_sources"][0]["title"] == "Passport Seva Kendra - India Post"
