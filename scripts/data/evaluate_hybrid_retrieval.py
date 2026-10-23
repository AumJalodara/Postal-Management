"""
Comprehensive Retrieval Evaluation Engine for Module 3 Step 4:
Hybrid Lexical + Dense Semantic Retrieval Evaluation.

Evaluates the production PostalRetrievalService across all 3 modes:
1. Lexical Baseline (PostgreSQL ts_rank_cd)
2. Dense Semantic (all-MiniLM-L6-v2 cosine similarity)
3. Hybrid RRF (k=60)

Runs against the unchanged 35-query postal benchmark (retrieval_queries.jsonl).
Computes Recall@1/3/5/10, Precision@5, MRR, nDCG@5, and latency metrics.
Separates model initialization time from warm-query execution latency.
Outputs: data/postal_documents/evaluation/hybrid_retrieval_evaluation.json
"""

import sys
import json
import math
import time
import statistics
from pathlib import Path
from typing import Dict, Any, List, Tuple

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = WORKSPACE_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.postal_retrieval_service import PostalRetrievalService
from app.services.dense_retrieval_service import DenseRetrievalManager

QUERIES_FILE = WORKSPACE_ROOT / "data" / "postal_documents" / "evaluation" / "retrieval_queries.jsonl"
EVALUATION_OUTPUT = WORKSPACE_ROOT / "data" / "postal_documents" / "evaluation" / "hybrid_retrieval_evaluation.json"


def compute_dcg(relevances: List[int], k: int) -> float:
    dcg = 0.0
    for i, rel in enumerate(relevances[:k], start=1):
        if rel > 0:
            dcg += (math.pow(2, rel) - 1.0) / math.log2(i + 1.0)
    return dcg


def compute_ndcg(retrieved_chunk_ids: List[str], ground_truth_grades: Dict[str, int], k: int = 5) -> float:
    retrieved_rels = [ground_truth_grades.get(cid, 0) for cid in retrieved_chunk_ids[:k]]
    actual_dcg = compute_dcg(retrieved_rels, k)

    ideal_rels = sorted(ground_truth_grades.values(), reverse=True)
    ideal_dcg = compute_dcg(ideal_rels, k)

    if ideal_dcg == 0.0:
        return 0.0
    return round(actual_dcg / ideal_dcg, 4)


def evaluate_mode(
    service: PostalRetrievalService,
    mode: str,
    queries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Evaluates a single retrieval mode across all benchmark queries."""
    recalls = {1: [], 3: [], 5: [], 10: []}
    precisions_5 = []
    reciprocal_ranks = []
    ndcgs_5 = []
    latencies = []
    failed_k5 = []
    per_query = []

    for q in queries:
        qid = q["query_id"]
        q_text = q["query"]
        expected_ids = set(q["expected_chunk_ids"])
        grades = q.get("relevance_grades", {cid: 2 for cid in expected_ids})

        resp = service.search(query=q_text, top_k=10, mode=mode)
        retrieved_ids = [r.chunk_id for r in resp.results]
        latencies.append(resp.latency_ms)

        # Recalls
        for k in [1, 3, 5, 10]:
            k_retrieved = set(retrieved_ids[:k])
            hit = 1.0 if any(cid in k_retrieved for cid in expected_ids) else 0.0
            recalls[k].append(hit)

        # Precision@5
        top_5 = retrieved_ids[:5]
        relevant_in_top_5 = sum(1 for cid in top_5 if grades.get(cid, 0) > 0)
        p_5 = relevant_in_top_5 / 5.0
        precisions_5.append(p_5)

        # MRR
        rr = 0.0
        first_rel_rank = None
        for rank, cid in enumerate(retrieved_ids, start=1):
            if grades.get(cid, 0) > 0:
                rr = 1.0 / rank
                first_rel_rank = rank
                break
        reciprocal_ranks.append(rr)

        # nDCG@5
        ndcg_5 = compute_ndcg(retrieved_ids, grades, k=5)
        ndcgs_5.append(ndcg_5)

        is_k5_success = recalls[5][-1] == 1.0
        if not is_k5_success:
            failed_k5.append({
                "query_id": qid,
                "query": q_text,
                "category": q.get("query_category", ""),
                "expected": list(expected_ids),
                "retrieved_top_5": retrieved_ids[:5],
                "first_relevant_rank": first_rel_rank
            })

        per_query.append({
            "query_id": qid,
            "query": q_text,
            "expected_chunk_ids": list(expected_ids),
            "retrieved_top_5": retrieved_ids[:5],
            "first_relevant_rank": first_rel_rank,
            "recall_at_1": recalls[1][-1],
            "recall_at_3": recalls[3][-1],
            "recall_at_5": recalls[5][-1],
            "recall_at_10": recalls[10][-1],
            "precision_at_5": round(p_5, 4),
            "reciprocal_rank": round(rr, 4),
            "ndcg_at_5": ndcg_5,
            "latency_ms": resp.latency_ms
        })

    return {
        "mode": mode,
        "recall_at_1": round(statistics.mean(recalls[1]), 4),
        "recall_at_3": round(statistics.mean(recalls[3]), 4),
        "recall_at_5": round(statistics.mean(recalls[5]), 4),
        "recall_at_10": round(statistics.mean(recalls[10]), 4),
        "precision_at_5": round(statistics.mean(precisions_5), 4),
        "mrr": round(statistics.mean(reciprocal_ranks), 4),
        "ndcg_at_5": round(statistics.mean(ndcgs_5), 4),
        "latency_mean_ms": round(statistics.mean(latencies), 2),
        "latency_median_ms": round(statistics.median(latencies), 2),
        "latency_min_ms": round(min(latencies), 2),
        "latency_max_ms": round(max(latencies), 2),
        "failed_k5_count": len(failed_k5),
        "failed_k5_queries": failed_k5,
        "per_query": per_query
    }


def run_evaluation() -> Dict[str, Any]:
    print("=" * 75)
    print(" MODULE 3 STEP 4: PRODUCTION HYBRID RETRIEVAL BENCHMARK")
    print("=" * 75)

    if not QUERIES_FILE.exists():
        raise FileNotFoundError(f"Queries file not found: {QUERIES_FILE}")

    queries = []
    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line.strip()))

    print(f"Loaded {len(queries)} benchmark queries from: {QUERIES_FILE}")

    # Database & Service initialization
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    service = PostalRetrievalService(session)

    # 1. Measure model initialization separately
    print("\nMeasuring one-time model initialization...")
    t0 = time.perf_counter()
    dense_mgr = DenseRetrievalManager.get_instance()
    init_time_ms = (time.perf_counter() - t0) * 1000.0
    print(f"Model initialization time: {init_time_ms:.2f} ms")

    # Warm-up query
    service.search("warmup query", top_k=1, mode="hybrid")

    # 2. Evaluate Lexical Mode
    print("\n[1/3] Evaluating Mode: 'lexical' (PostgreSQL Native FTS)...")
    results_lexical = evaluate_mode(service, "lexical", queries)

    # 3. Evaluate Dense Mode
    print("[2/3] Evaluating Mode: 'dense' (all-MiniLM-L6-v2 Cosine Similarity)...")
    results_dense = evaluate_mode(service, "dense", queries)

    # 4. Evaluate Hybrid Mode
    print("[3/3] Evaluating Mode: 'hybrid' (Reciprocal Rank Fusion k=60)...")
    results_hybrid = evaluate_mode(service, "hybrid", queries)

    session.close()

    # Query comparison table
    comparison_table = []
    improved_queries = []
    degraded_queries = []
    unchanged_queries = []

    for idx, q in enumerate(queries):
        qid = q["query_id"]
        lex_rank = results_lexical["per_query"][idx]["first_relevant_rank"]
        dense_rank = results_dense["per_query"][idx]["first_relevant_rank"]
        hybrid_rank = results_hybrid["per_query"][idx]["first_relevant_rank"]

        lex_rec5 = results_lexical["per_query"][idx]["recall_at_5"]
        hybrid_rec5 = results_hybrid["per_query"][idx]["recall_at_5"]

        if hybrid_rec5 > lex_rec5 or (lex_rank is not None and hybrid_rank is not None and hybrid_rank < lex_rank):
            status = "IMPROVED"
            improved_queries.append(qid)
        elif hybrid_rec5 < lex_rec5 or (lex_rank is not None and hybrid_rank is not None and hybrid_rank > lex_rank):
            status = "DEGRADED"
            degraded_queries.append(qid)
        else:
            status = "UNCHANGED"
            unchanged_queries.append(qid)

        comparison_table.append({
            "query_id": qid,
            "query": q["query"],
            "expected_chunk_ids": q["expected_chunk_ids"],
            "lexical_rank": lex_rank,
            "dense_rank": dense_rank,
            "hybrid_rank": hybrid_rank,
            "status": status
        })

    # Summary report structure
    report = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "corpus_chunks": 228,
            "benchmark_queries": len(queries),
            "model_id": settings.DENSE_MODEL_ID,
            "model_init_time_ms": round(init_time_ms, 2),
            "rrf_k": service.rrf_k,
            "execution_mode": "100% Local CPU, local_files_only=True"
        },
        "summary_table": {
            "metric": [
                "Recall@1", "Recall@3", "Recall@5", "Recall@10",
                "Precision@5", "MRR", "nDCG@5",
                "Median Latency", "Mean Latency", "Top-5 Failures"
            ],
            "mode_lexical": [
                f"{results_lexical['recall_at_1']*100:.2f}%",
                f"{results_lexical['recall_at_3']*100:.2f}%",
                f"{results_lexical['recall_at_5']*100:.2f}%",
                f"{results_lexical['recall_at_10']*100:.2f}%",
                f"{results_lexical['precision_at_5']:.4f}",
                f"{results_lexical['mrr']:.4f}",
                f"{results_lexical['ndcg_at_5']:.4f}",
                f"{results_lexical['latency_median_ms']:.2f} ms",
                f"{results_lexical['latency_mean_ms']:.2f} ms",
                f"{results_lexical['failed_k5_count']}/{len(queries)}"
            ],
            "mode_dense": [
                f"{results_dense['recall_at_1']*100:.2f}%",
                f"{results_dense['recall_at_3']*100:.2f}%",
                f"{results_dense['recall_at_5']*100:.2f}%",
                f"{results_dense['recall_at_10']*100:.2f}%",
                f"{results_dense['precision_at_5']:.4f}",
                f"{results_dense['mrr']:.4f}",
                f"{results_dense['ndcg_at_5']:.4f}",
                f"{results_dense['latency_median_ms']:.2f} ms",
                f"{results_dense['latency_mean_ms']:.2f} ms",
                f"{results_dense['failed_k5_count']}/{len(queries)}"
            ],
            "mode_hybrid": [
                f"{results_hybrid['recall_at_1']*100:.2f}%",
                f"{results_hybrid['recall_at_3']*100:.2f}%",
                f"{results_hybrid['recall_at_5']*100:.2f}%",
                f"{results_hybrid['recall_at_10']*100:.2f}%",
                f"{results_hybrid['precision_at_5']:.4f}",
                f"{results_hybrid['mrr']:.4f}",
                f"{results_hybrid['ndcg_at_5']:.4f}",
                f"{results_hybrid['latency_median_ms']:.2f} ms",
                f"{results_hybrid['latency_mean_ms']:.2f} ms",
                f"{results_hybrid['failed_k5_count']}/{len(queries)}"
            ]
        },
        "query_deltas": {
            "improved_queries": improved_queries,
            "degraded_queries": degraded_queries,
            "unchanged_queries": unchanged_queries
        },
        "modes": {
            "lexical": results_lexical,
            "dense": results_dense,
            "hybrid": results_hybrid
        },
        "comparison_table": comparison_table
    }

    EVALUATION_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(EVALUATION_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 75)
    print(" RETRIEVAL BENCHMARK RESULTS")
    print("=" * 75)
    print(f"{'Metric':<18} | {'Lexical Mode':<15} | {'Dense Mode':<15} | {'Hybrid Mode':<15}")
    print("-" * 75)
    for m, l, d, h in zip(
        report["summary_table"]["metric"],
        report["summary_table"]["mode_lexical"],
        report["summary_table"]["mode_dense"],
        report["summary_table"]["mode_hybrid"]
    ):
        print(f"{m:<18} | {l:<15} | {d:<15} | {h:<15}")
    print("=" * 75)
    print(f"\nImproved Queries  : {len(improved_queries)}: {improved_queries}")
    print(f"Degraded Queries  : {len(degraded_queries)}: {degraded_queries}")
    print(f"Unchanged Queries : {len(unchanged_queries)}: {unchanged_queries}")
    print(f"\nReport Saved To: {EVALUATION_OUTPUT}")
    print("=" * 75 + "\n")

    return report


if __name__ == "__main__":
    run_evaluation()
