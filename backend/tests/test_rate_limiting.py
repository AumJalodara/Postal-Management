"""
Regression tests for Finding SEC-003: Rate Limiting & Abuse Prevention.
Verifies:
1. Endpoints succeed when called within configured rate limits.
2. Endpoints return HTTP 429 Too Many Requests when limits are exceeded.
3. 429 responses conform to the uniform error envelope:
   {"success": False, "error": {"code": "RATE_LIMIT_EXCEEDED", ...}}
4. Retry-After header is returned.
5. IP-based client isolation ensures one IP's burst does not block another IP.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.limiter import limiter


@pytest.fixture(autouse=True)
def reset_limiter_state():
    """Reset the limiter storage between tests to avoid cross-test interference."""
    limiter.reset()
    yield
    limiter.reset()


def test_login_rate_limiting():
    """Verify POST /api/v1/auth/login triggers HTTP 429 after 5 rapid requests from the same IP."""
    client = TestClient(app)
    ip_headers = {"X-Forwarded-For": "198.51.100.1"}

    # Attempt 5 failed logins (allowed within rate limit 5/minute)
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "ratelimit_test@example.com", "password": "WrongPassword123!"},
            headers=ip_headers
        )
        assert resp.status_code in [401, 404, 422], f"Attempt {i+1} got unexpected status {resp.status_code}"

    # 6th request from the same IP must be rejected with HTTP 429
    burst_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "ratelimit_test@example.com", "password": "WrongPassword123!"},
        headers=ip_headers
    )
    assert burst_resp.status_code == 429
    assert "Retry-After" in burst_resp.headers

    data = burst_resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Too many requests" in data["error"]["message"]


def test_rate_limiting_client_ip_isolation():
    """Verify that exhausting rate limits from IP A does not block requests from IP B."""
    client = TestClient(app)
    ip_a = {"X-Forwarded-For": "198.51.100.10"}
    ip_b = {"X-Forwarded-For": "198.51.100.20"}

    # Exhaust limit for IP A
    for _ in range(5):
        client.post(
            "/api/v1/auth/login",
            json={"email": "ip_a@example.com", "password": "WrongPassword123!"},
            headers=ip_a
        )

    # 6th request from IP A is 429
    resp_a = client.post(
        "/api/v1/auth/login",
        json={"email": "ip_a@example.com", "password": "WrongPassword123!"},
        headers=ip_a
    )
    assert resp_a.status_code == 429

    # First request from IP B must still be permitted (not 429)
    resp_b = client.post(
        "/api/v1/auth/login",
        json={"email": "ip_b@example.com", "password": "WrongPassword123!"},
        headers=ip_b
    )
    assert resp_b.status_code != 429


from unittest.mock import patch
from app.schemas.rag import RAGResponse, CitationDetail

def test_postal_ask_rate_limiting():
    """Verify POST /api/v1/postal/ask triggers rate limiting after exceeding RATE_LIMIT_RAG."""
    client = TestClient(app)
    ip_headers = {"X-Forwarded-For": "198.51.100.30"}
    
    mock_rag_response = RAGResponse(
        query="What is speed post?",
        answer="Speed post is an express service.",
        citations=[CitationDetail(citation_id=1, document_id="DOC1", document_title="Act", chunk_id="DOC1_001", page=1, source_pages=[1], legal_reference="Section 1")],
        retrieved_chunks=1,
        grounded=True,
        insufficient_evidence=False,
        retrieval_mode="hybrid"
    )

    with patch("app.routes.postal.RAGSynthesisService.ask", return_value=mock_rag_response):
        # Make 10 requests (allowed within 10/minute)
        for _ in range(10):
            resp = client.post(
                "/api/v1/postal/ask",
                json={"query": "What is the speed post delivery time?", "top_k": 3, "retrieval_mode": "hybrid"},
                headers=ip_headers
            )
            assert resp.status_code == 200, f"Unexpected status {resp.status_code}"

        # 11th request must trigger rate limit 429
        burst_resp = client.post(
            "/api/v1/postal/ask",
            json={"query": "What is the speed post delivery time?", "top_k": 3, "retrieval_mode": "hybrid"},
            headers=ip_headers
        )
        assert burst_resp.status_code == 429
        assert burst_resp.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"

