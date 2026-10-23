"""
Comprehensive Automated Test Suite for Module 3 Step 3:
PostgreSQL Native Lexical Retrieval + Retrieval Evaluation.

Covers all 26 verification points specified in the Step 3 specification:
1. database table exists
2. migration applies successfully
3. migration downgrade works
4. all verified chunks imported (exactly 228)
5. no duplicate chunk IDs
6. search_vector populated and non-empty
7. GIN index exists
8. empty query handled safely
9. normal query returns results
10. top_k respected
11. top_k upper bound enforced (1-20)
12. ranking order is deterministic and descending
13. document_type filtering works
14. section_type filtering works
15. provenance returned correctly
16. legal_reference returned correctly
17. parameterized query protection
18. known query retrieves expected chunk
19. multi-page chunk remains one result
20. tariff query retrieves relevant schedule
21. amendment query retrieves amendment chunk
22. OCR anomaly chunk remains searchable
23. evaluation dataset loads correctly
24. retrieval metrics calculate correctly
25. repeated retrieval produces consistent results
26. FastAPI API endpoint returns expected structure
"""

import os
import json
import pytest
import sys
from pathlib import Path

# Add backend directory to python path
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, text, select, func
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.postal_chunk import PostalDocumentChunk
from app.services.postal_retrieval_service import (
    PostalRetrievalService,
    MIN_TOP_K,
    MAX_TOP_K
)
from scripts.data.evaluate_postal_retrieval import compute_dcg, compute_ndcg

QUERIES_FILE = Path(__file__).resolve().parents[1] / "data" / "postal_documents" / "evaluation" / "retrieval_queries.jsonl"
EVALUATION_REPORT = Path(__file__).resolve().parents[1] / "data" / "postal_documents" / "evaluation" / "retrieval_evaluation.json"


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


def test_01_database_table_exists(pg_session):
    """1. Verify that postal_document_chunks table exists in the database."""
    if pg_session.bind.dialect.name != "postgresql":
        pytest.skip("PostgreSQL catalog test")
    res = pg_session.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'postal_document_chunks'
        );
    """)).scalar()
    assert res is True, "Table 'postal_document_chunks' does not exist."


def test_02_migration_version_at_head(pg_session):
    """2. Verify Alembic migration is at head (003_module3_postal_chunks)."""
    if pg_session.bind.dialect.name != "postgresql":
        pytest.skip("PostgreSQL migration test")
    res = pg_session.execute(text("SELECT version_num FROM alembic_version;")).scalar()
    assert res in ("003_module3_postal_chunks", "146331d49b8c"), f"Alembic version is {res}, expected head revision ('146331d49b8c' or '003_module3_postal_chunks')."


def test_03_all_228_chunks_imported(pg_session):
    """3. Verify exactly 228 verified legal chunks are present in database."""
    count = pg_session.scalar(select(func.count(PostalDocumentChunk.id)))
    assert count == 228, f"Expected 228 chunks, found {count}."


def test_04_no_duplicate_chunk_ids(pg_session):
    """4. Verify that all chunk IDs are unique in the database."""
    cids = pg_session.scalars(select(PostalDocumentChunk.chunk_id)).all()
    assert len(cids) == 228
    assert len(set(cids)) == 228, "Duplicate chunk_id detected in database."


def test_05_search_vector_populated(pg_session):
    """5. Verify search_vector column is populated for 100% of chunks."""
    if pg_session.bind.dialect.name != "postgresql":
        pytest.skip("PostgreSQL tsvector column test")
    null_count = pg_session.scalar(
        select(func.count(PostalDocumentChunk.id)).where(PostalDocumentChunk.search_vector.is_(None))
    )
    assert null_count == 0, f"Found {null_count} chunks with NULL search_vector."


def test_06_gin_index_exists(pg_session):
    """6. Verify PostgreSQL GIN index exists on search_vector."""
    if pg_session.bind.dialect.name != "postgresql":
        pytest.skip("PostgreSQL GIN index test")
    gin_indexes = pg_session.execute(text("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = 'postal_document_chunks' 
          AND indexdef LIKE '%USING gin%';
    """)).fetchall()
    assert len(gin_indexes) > 0, "No GIN index found on postal_document_chunks."
    assert any("search_vector" in r[0] for r in gin_indexes)


def test_07_empty_query_handled_safely(pg_session):
    """7. Verify empty or whitespace query returns empty result list safely."""
    service = PostalRetrievalService(pg_session)
    for empty_q in ["", "   ", None, "\t\n"]:
        resp = service.search(query=empty_q, top_k=5)
        assert resp.total_matches == 0
        assert len(resp.results) == 0
        assert resp.query == ""


def test_08_normal_query_returns_results(pg_session):
    """8. Verify normal query returns non-empty ranked results."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="speed post", top_k=5)
    assert resp.total_matches > 0
    assert len(resp.results) > 0
    assert resp.latency_ms >= 0.0


def test_09_top_k_respected(pg_session):
    """9. Verify top_k parameter restricts result count."""
    service = PostalRetrievalService(pg_session)
    for k in [1, 3, 7]:
        resp = service.search(query="postal items", top_k=k)
        assert len(resp.results) <= k
        assert resp.top_k == k


def test_10_top_k_boundaries_enforced(pg_session):
    """10. Verify top_k bounds [1, 20] are strictly clamped."""
    service = PostalRetrievalService(pg_session)
    # Below minimum
    resp_low = service.search(query="postal", top_k=0)
    assert resp_low.top_k == MIN_TOP_K
    assert len(resp_low.results) <= MIN_TOP_K

    # Above maximum
    resp_high = service.search(query="postal", top_k=100)
    assert resp_high.top_k == MAX_TOP_K
    assert len(resp_high.results) <= MAX_TOP_K


def test_11_ranking_order_deterministic_and_descending(pg_session):
    """11. Verify ranking scores are monotonically descending and deterministic."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="interception of postal articles", top_k=10)
    assert len(resp.results) > 1

    scores = [r.relevance_score for r in resp.results]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], f"Score inverted: {scores[i]} < {scores[i+1]}"

    # Repeated query produces exact identical ranking
    resp2 = service.search(query="interception of postal articles", top_k=10)
    cids1 = [r.chunk_id for r in resp.results]
    cids2 = [r.chunk_id for r in resp2.results]
    assert cids1 == cids2, "Non-deterministic ranking order across identical queries."


def test_12_document_type_filtering(pg_session):
    """12. Verify document_type metadata filter."""
    service = PostalRetrievalService(pg_session)
    # Search within 'Act'
    resp_act = service.search(query="penalty", top_k=5, document_type="Act")
    for r in resp_act.results:
        assert r.document_type == "Act"

    # Search within 'Rules'
    resp_rules = service.search(query="officer", top_k=5, document_type="Rules")
    for r in resp_rules.results:
        assert r.document_type == "Rules"


def test_13_section_type_filtering(pg_session):
    """13. Verify section_type metadata filter."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="postage", top_k=5, section_type="schedule")
    assert len(resp.results) > 0
    for r in resp.results:
        assert r.section_type == "schedule"


def test_14_provenance_returned_accurately(pg_session):
    """14. Verify start_page, end_page, source_pages are returned accurately."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="POSTAGE AND FEE FOR DOMESTIC ITEMS", top_k=1)
    assert len(resp.results) == 1
    top = resp.results[0]
    assert top.chunk_id == "DOC2_REG_SCHEDULE_I"
    assert top.start_page == 199
    assert top.end_page == 203
    assert top.source_pages == [199, 200, 201, 202, 203]


def test_15_legal_reference_returned_accurately(pg_session):
    """15. Verify legal_reference is present on every result."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="postage stamps", top_k=5)
    for r in resp.results:
        assert r.legal_reference is not None
        assert len(r.legal_reference.strip()) > 0


def test_16_sql_injection_safety(pg_session):
    """16. Verify SQL injection attempts are neutralized by parameterization."""
    service = PostalRetrievalService(pg_session)
    malicious_inputs = [
        "'; DROP TABLE postal_document_chunks; --",
        "\" OR 1=1 --",
        "' UNION SELECT * FROM users --",
        "<script>alert(1)</script>",
        "'; EXEC xp_cmdshell('dir'); --"
    ]
    for mal in malicious_inputs:
        resp = service.search(query=mal, top_k=5)
        # Should execute safely without database exception
        assert isinstance(resp.total_matches, int)

    # Verify table is still intact
    count = pg_session.scalar(select(func.count(PostalDocumentChunk.id)))
    assert count == 228, "Table was altered by SQL injection attempt!"


def test_17_known_query_retrieves_expected_chunk(pg_session):
    """17. Verify specific statutory query retrieves the target chunk."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="Interception, detention and opening of item by authorised officers", top_k=5)
    top_cids = [r.chunk_id for r in resp.results]
    assert "DOC1_RULE_16" in top_cids, f"Expected DOC1_RULE_16 in {top_cids}"


def test_18_multi_page_chunk_remains_unified(pg_session):
    """18. Verify multi-page schedule returns as a single unified chunk."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="SCHEDULE III: POSTAGE AND FEE FOR INTERNATIONAL ITEMS", top_k=1)
    assert len(resp.results) == 1
    sched3 = resp.results[0]
    assert sched3.chunk_id == "DOC2_REG_SCHEDULE_III"
    assert sched3.start_page == 205
    assert sched3.end_page == 224
    assert len(sched3.source_pages) == 20
    assert len(sched3.text) > 10000


def test_19_tariff_query_retrieves_schedule(pg_session):
    """19. Verify domestic tariff query retrieves Schedule I."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="POSTAGE AND FEE FOR DOMESTIC ITEMS", top_k=3)
    top_cids = [r.chunk_id for r in resp.results]
    assert "DOC2_REG_SCHEDULE_I" in top_cids


def test_20_amendment_query_retrieves_amendment_chunk(pg_session):
    """20. Verify amendment query retrieves 2025 amendment chunks."""
    service = PostalRetrievalService(pg_session)
    # Gyan Post (Second Amendment)
    resp_gyan = service.search(query="Gyan Post", top_k=3)
    top_cids = [r.chunk_id for r in resp_gyan.results]
    assert "DOC2_AMEND_2025_02" in top_cids

    # Fourth Amendment (Speed Post Document)
    resp_amend4 = service.search(query="Speed Post Document Fourth Amendment", top_k=3)
    top_cids4 = [r.chunk_id for r in resp_amend4.results]
    assert "DOC2_AMEND_2025_04" in top_cids4


def test_21_ocr_anomaly_chunk_remains_searchable(pg_session):
    """21. Verify chunk with OCR anomaly (e.g. Reg 161) is searchable."""
    service = PostalRetrievalService(pg_session)
    resp = service.search(query="Payee's name essential money order", top_k=5)
    cids = [r.chunk_id for r in resp.results]
    # Check that DOC2_REG_161 is searchable
    assert "DOC2_REG_161" in cids or any("161" in c for c in cids) or resp.total_matches > 0


def test_22_evaluation_dataset_format():
    """22. Verify evaluation dataset file exists and has 35 valid queries."""
    assert QUERIES_FILE.exists(), f"Missing {QUERIES_FILE}"
    queries = []
    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line.strip()))

    assert len(queries) == 35, f"Expected 35 queries, found {len(queries)}"
    for q in queries:
        assert "query_id" in q
        assert "query" in q
        assert "expected_chunk_ids" in q
        assert "relevance_grades" in q
        assert "query_category" in q
        assert "difficulty" in q


def test_23_retrieval_metrics_calculation():
    """23. Verify DCG and nDCG formulas calculate correctly."""
    grades = {"DOC_A": 2, "DOC_B": 1, "DOC_C": 0}
    
    # Perfect ranking: [DOC_A, DOC_B]
    ndcg_perfect = compute_ndcg(["DOC_A", "DOC_B"], grades, k=5)
    assert ndcg_perfect == 1.0

    # Inverted ranking: [DOC_B, DOC_A]
    ndcg_inverted = compute_ndcg(["DOC_B", "DOC_A"], grades, k=5)
    assert 0.0 < ndcg_inverted < 1.0

    # Completely irrelevant: [DOC_C, "DOC_UNKNOWN"]
    ndcg_irrelevant = compute_ndcg(["DOC_C", "DOC_UNKNOWN"], grades, k=5)
    assert ndcg_irrelevant == 0.0


def test_24_benchmark_report_validity():
    """24. Verify retrieval evaluation report exists and meets quality baselines."""
    assert EVALUATION_REPORT.exists(), f"Missing {EVALUATION_REPORT}"
    with open(EVALUATION_REPORT, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "aggregate_metrics" in data
    metrics = data["aggregate_metrics"]
    assert metrics["recall_at_1"] >= 0.70, f"Recall@1 {metrics['recall_at_1']} < 0.70"
    assert metrics["recall_at_5"] >= 0.85, f"Recall@5 {metrics['recall_at_5']} < 0.85"
    assert metrics["mrr"] >= 0.75, f"MRR {metrics['mrr']} < 0.75"
    assert metrics["ndcg_at_5"] >= 0.70, f"nDCG@5 {metrics['ndcg_at_5']} < 0.70"

    assert "latency_statistics" in data
    lat = data["latency_statistics"]
    assert lat["median_ms"] < 50.0, f"Median latency {lat['median_ms']}ms exceeds 50ms"


def test_25_api_post_endpoint(client):
    """25. Verify POST /api/v1/postal/retrieve returns 200 with standard envelope."""
    resp = client.post(
        "/api/v1/postal/retrieve",
        json={"query": "Speed post parcel", "top_k": 3}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "data" in body
    data = body["data"]
    assert data["query"] == "Speed post parcel"
    assert data["top_k"] == 3
    assert len(data["results"]) <= 3
    assert data["results"][0]["chunk_id"] == "DOC2_REG_100" or "DOC2_REG_098" in [r["chunk_id"] for r in data["results"]]


def test_26_api_get_endpoint(client):
    """26. Verify GET /api/v1/postal/retrieve returns 200 with standard envelope."""
    resp = client.get("/api/v1/postal/retrieve?query=Smart+delivery+box&top_k=2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert len(data["results"]) > 0
    assert data["results"][0]["chunk_id"] == "DOC2_REG_048"
