"""
Regression tests for Finding RAG-001: Graceful Degradation on Missing Dense Embeddings.
Verifies:
1. DenseRetrievalManager reports availability status cleanly without crashing on startup.
2. When dense embeddings are unavailable, PostalRetrievalService gracefully falls back
   to lexical full-text search with cover-density ranking rather than raising RuntimeError.
3. Hybrid and dense search modes return valid, consistent response envelopes in fallback mode.
"""

from unittest.mock import patch, MagicMock
from app.services.dense_retrieval_service import DenseRetrievalManager
from app.services.postal_retrieval_service import PostalRetrievalService
from app.database.connection import SessionLocal


def test_dense_manager_normal_availability():
    """When embeddings files are present, DenseRetrievalManager is available."""
    dense_mgr = DenseRetrievalManager.get_instance()
    assert dense_mgr.is_available is True
    assert dense_mgr.error_reason is None


def test_hybrid_search_graceful_lexical_fallback():
    """When dense vectors are unavailable, hybrid search must gracefully degrade to lexical search."""
    db = SessionLocal()
    try:
        service = PostalRetrievalService(db)

        # Mock DenseRetrievalManager as unavailable (e.g. missing npz file)
        mock_dense = MagicMock()
        mock_dense.is_available = False
        mock_dense.error_reason = "Test simulated missing postal_chunk_embeddings.npz"

        with patch("app.services.postal_retrieval_service.DenseRetrievalManager.get_instance", return_value=mock_dense):
            resp = service.search(query="Section 9 Post Office Act", top_k=5, mode="hybrid")
            assert resp is not None
            assert resp.total_matches > 0
            assert len(resp.results) > 0
            # Ensure results indicate fallback mode
            assert any(r.retrieval_mode == "hybrid_fallback" for r in resp.results)
    finally:
        db.close()


def test_dense_search_graceful_lexical_fallback():
    """When dense vectors are unavailable, pure dense search must gracefully degrade to lexical search."""
    db = SessionLocal()
    try:
        service = PostalRetrievalService(db)

        mock_dense = MagicMock()
        mock_dense.is_available = False
        mock_dense.error_reason = "Test simulated missing postal_chunk_embeddings.npz"

        with patch("app.services.postal_retrieval_service.DenseRetrievalManager.get_instance", return_value=mock_dense):
            resp = service.search(query="speed post delivery conditions", top_k=5, mode="dense")
            assert resp is not None
            assert resp.total_matches > 0
            assert len(resp.results) > 0
            assert any(r.retrieval_mode == "dense_fallback" for r in resp.results)
    finally:
        db.close()
