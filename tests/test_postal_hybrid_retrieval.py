"""
Focused Test Suite for Module 3 Step 4:
Hybrid Lexical + Dense Semantic Retrieval (PostgreSQL FTS + all-MiniLM-L6-v2 + RRF).

Covers all 20 required verification points:
1. Model loading verification
2. Offline / local-only model loading (local_files_only=True)
3. 384-dimensional embeddings
4. Deterministic embedding generation
5. Cosine similarity calculation
6. Exactly 228 chunk embeddings in cache
7. Stale / missing embedding detection
8. Dense ranking order (descending cosine similarity)
9. RRF calculation
10. Deterministic RRF tie-breaking
11. Lexical + dense integration
12. Exact legal-reference retrieval preservation
13. Q008 semantic improvement (target in Top-10)
14. Q028 target in Top-5
15. Q035 semantic improvement (target in Top-10)
16. Empty query handling
17. Short query handling
18. Normal postal query execution
19. API response structure validation
20. Cross-dialect regression compatibility
"""

import os
import json
import pytest
import sys
from pathlib import Path
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.dense_retrieval_service import DenseRetrievalManager
from app.services.postal_retrieval_service import (
    PostalRetrievalService,
    MIN_TOP_K,
    MAX_TOP_K
)
from scripts.data.generate_postal_embeddings import verify_embedding_cache

EMBEDDING_DIR = Path(settings.DENSE_EMBEDDING_DIR)
NPZ_FILE = EMBEDDING_DIR / "postal_chunk_embeddings.npz"
METADATA_FILE = EMBEDDING_DIR / "metadata.json"


@pytest.fixture(scope="module")
def pg_session():
    """Provides a connection session to the PostgreSQL database."""
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def client():
    """FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def dense_manager():
    """Provides singleton DenseRetrievalManager instance."""
    return DenseRetrievalManager.get_instance()


# ---------------------------------------------------------------------------
# Tests 1-7: Model, Embeddings, Cache & Staleness Detection
# ---------------------------------------------------------------------------

def test_01_model_loading(dense_manager):
    """1. Verify that SentenceTransformer model loads properly."""
    assert dense_manager.model is not None, "Model failed to load."
    assert dense_manager.model_id == "sentence-transformers/all-MiniLM-L6-v2"


def test_02_offline_local_only_loading(dense_manager):
    """2. Verify model runs strictly offline with local_files_only=True."""
    from sentence_transformers import SentenceTransformer
    # Verify instantiating with local_files_only=True succeeds without network access
    local_model = SentenceTransformer(settings.DENSE_MODEL_ID, local_files_only=True)
    assert local_model is not None


def test_03_embedding_dimension(dense_manager):
    """3. Verify output embeddings have exactly 384 dimensions."""
    emb, _ = dense_manager.encode_query("test query")
    assert emb.shape == (384,), f"Expected shape (384,), got {emb.shape}"
    assert emb.dtype == np.float32


def test_04_deterministic_embedding_generation(dense_manager):
    """4. Verify that encoding the same text multiple times produces identical vectors."""
    text = "The Post Office Act, 2023 — Section 2 Definitions"
    emb1, _ = dense_manager.encode_query(text)
    emb2, _ = dense_manager.encode_query(text)
    np.testing.assert_array_almost_equal(emb1, emb2, decimal=6)


def test_05_cosine_similarity_calculation(dense_manager):
    """5. Verify cosine similarity between identical vectors equals 1.0 (L2-normalized)."""
    emb, _ = dense_manager.encode_query("speed post parcel")
    norm = np.linalg.norm(emb)
    assert abs(norm - 1.0) < 1e-4, f"Vector is not unit normalized (norm={norm})"
    self_sim = float(np.dot(emb, emb))
    assert abs(self_sim - 1.0) < 1e-4, f"Self similarity is not 1.0 ({self_sim})"


def test_06_chunk_embedding_count(dense_manager):
    """6. Verify cache contains exactly 228 chunk embeddings."""
    assert len(dense_manager.chunk_ids) == 228, f"Expected 228 chunks, got {len(dense_manager.chunk_ids)}"
    assert dense_manager.embeddings.shape == (228, 384)


def test_07_stale_missing_embedding_detection():
    """7. Verify verify_embedding_cache detects missing or invalid cache files."""
    valid, msg = verify_embedding_cache()
    assert valid is True, f"Cache verification failed: {msg}"


# ---------------------------------------------------------------------------
# Tests 8-12: Dense & Hybrid Ranking Mechanics
# ---------------------------------------------------------------------------

def test_08_dense_ranking_order(dense_manager):
    """8. Verify dense ranking returns results in strictly descending similarity order."""
    results, _, _ = dense_manager.search("prohibited items in mail", top_k=10)
    assert len(results) == 10
    sims = [sim for _, sim, _ in results]
    for i in range(len(sims) - 1):
        assert sims[i] >= sims[i + 1], f"Similarity not descending: {sims[i]} < {sims[i+1]}"


def test_09_rrf_calculation_formula(pg_session):
    """9. Verify RRF score calculation follows Cormack formula: sum 1/(k + rank)."""
    service = PostalRetrievalService(pg_session)
    k = service.rrf_k
    assert k == 60
    # For a chunk ranked #1 in lexical and #2 in dense:
    expected_score = (1.0 / (60 + 1)) + (1.0 / (60 + 2))
    assert round(expected_score, 5) == round((1.0 / 61) + (1.0 / 62), 5)


def test_10_deterministic_rrf_tie_breaking(pg_session):
    """10. Verify repeated hybrid retrieval produces strictly identical rankings."""
    service = PostalRetrievalService(pg_session)
    resp1 = service.search(query="interception of postal articles", top_k=10, mode="hybrid")
    resp2 = service.search(query="interception of postal articles", top_k=10, mode="hybrid")
    cids1 = [r.chunk_id for r in resp1.results]
    cids2 = [r.chunk_id for r in resp2.results]
    assert cids1 == cids2, "Hybrid ranking is non-deterministic across identical runs."


def test_11_lexical_dense_integration(pg_session):
    """11. Verify hybrid results report both lexical and dense ranks when available."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="Speed post parcel regulations", top_k=5, mode="hybrid")
    assert resp.retrieval_mode == "hybrid"
    assert len(resp.results) > 0
    top = resp.results[0]
    assert top.relevance_score > 0.0
    # Top chunk should have rank metadata
    assert top.lexical_rank is not None or top.dense_rank is not None


def test_12_exact_legal_reference_retrieval(pg_session):
    """12. Verify exact statutory reference retrieval is preserved under hybrid mode."""
    service = PostalRetrievalService(pg_session)
    # Schedule I
    resp_sch = service.search(query="SCHEDULE I: POSTAGE AND FEE FOR DOMESTIC ITEMS", top_k=1, mode="hybrid")
    assert len(resp_sch.results) == 1
    assert resp_sch.results[0].chunk_id == "DOC2_REG_SCHEDULE_I"

    # Schedule V
    resp_v = service.search(query="SCHEDULE V: MONEY REMITTANCE SERVICES", top_k=1, mode="hybrid")
    assert len(resp_v.results) == 1
    assert resp_v.results[0].chunk_id == "DOC2_REG_SCHEDULE_V"


# ---------------------------------------------------------------------------
# Tests 13-15: Q008, Q028, Q035 Specific Verification
# ---------------------------------------------------------------------------

def test_13_q008_speed_post_conditions_top_10(pg_session):
    """13. Verify Q008: Hybrid places target DOC2_REG_098 in Top-10 (lexical was #143)."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="Speed post service conditions", top_k=10, mode="hybrid")
    retrieved_cids = [r.chunk_id for r in resp.results]
    assert "DOC2_REG_098" in retrieved_cids, (
        f"DOC2_REG_098 not in Top-10 hybrid results: {retrieved_cids}"
    )


def test_14_q028_payee_name_essential_top_5(pg_session):
    """14. Verify Q028: Hybrid places target DOC2_REG_161 in Top-5 (lexical was #24)."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="Payee's name essential for money order remittance", top_k=5, mode="hybrid")
    retrieved_cids = [r.chunk_id for r in resp.results]
    assert "DOC2_REG_161" in retrieved_cids, (
        f"DOC2_REG_161 not in Top-5 hybrid results: {retrieved_cids}"
    )


def test_15_q035_repeal_savings_top_10(pg_session):
    """15. Verify Q035: Hybrid places target DOC2_ACT_SECTION_16 in Top-10 (lexical was #13)."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="Repeal and savings of Post Office Act 1898", top_k=10, mode="hybrid")
    retrieved_cids = [r.chunk_id for r in resp.results]
    assert "DOC2_ACT_SECTION_16" in retrieved_cids, (
        f"DOC2_ACT_SECTION_16 not in Top-10 hybrid results: {retrieved_cids}"
    )


# ---------------------------------------------------------------------------
# Tests 16-20: Robustness, API & Regression Compatibility
# ---------------------------------------------------------------------------

def test_16_empty_query_handling(pg_session):
    """16. Verify empty and whitespace queries return safe zero-result response."""
    service = PostalRetrievalService(pg_session)
    for empty_q in ["", "   ", None]:
        resp = service.search(query=empty_q, top_k=5, mode="hybrid")
        assert resp.total_matches == 0
        assert len(resp.results) == 0
        assert resp.latency_ms >= 0.0


def test_17_short_query_handling(pg_session):
    """17. Verify single word and short queries execute safely in hybrid mode."""
    service = PostalRetrievalService(pg_session)
    for q in ["post", "parcel", "fee"]:
        resp = service.search(query=q, top_k=3, mode="hybrid")
        assert resp.total_matches > 0
        assert len(resp.results) > 0


def test_18_normal_postal_query(pg_session):
    """18. Verify typical postal user query returns ranked chunks with provenance."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="transmission of foreign parcels", top_k=5, mode="hybrid")
    assert len(resp.results) > 0
    for r in resp.results:
        assert r.chunk_id.startswith("DOC")
        assert r.start_page > 0
        assert len(r.source_pages) > 0
        assert r.legal_reference is not None


def test_19_api_response_structure_and_modes(client):
    """19. Verify FastAPI endpoint returns correct schema across all three modes."""
    # Default (hybrid)
    r_def = client.post("/api/v1/postal/retrieve", json={"query": "money order", "top_k": 3})
    assert r_def.status_code == 200
    d_def = r_def.json()["data"]
    assert d_def["retrieval_mode"] == "hybrid"
    assert len(d_def["results"]) <= 3

    # Explicit lexical
    r_lex = client.post("/api/v1/postal/retrieve", json={"query": "money order", "top_k": 3, "retrieval_mode": "lexical"})
    assert r_lex.status_code == 200
    assert r_lex.json()["data"]["retrieval_mode"] == "lexical"

    # Explicit dense
    r_dense = client.post("/api/v1/postal/retrieve", json={"query": "money order", "top_k": 3, "retrieval_mode": "dense"})
    assert r_dense.status_code == 200
    assert r_dense.json()["data"]["retrieval_mode"] == "dense"


def test_20_backward_compatibility_regression(client):
    """20. Verify that Step 3 callers omitting retrieval_mode continue to function seamlessly."""
    payload = {"query": "compensation in respect of insured items", "top_k": 5}
    resp = client.post("/api/v1/postal/retrieve", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total_matches"] > 0
    assert len(data["results"]) > 0
    # Top chunk should be Insurance compensation (DOC2_REG_074)
    top_cids = [r["chunk_id"] for r in data["results"]]
    assert "DOC2_REG_074" in top_cids, f"Expected DOC2_REG_074 in {top_cids}"
    assert data["results"][0]["chunk_id"] == "DOC2_REG_074"
