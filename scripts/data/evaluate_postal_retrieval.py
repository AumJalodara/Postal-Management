"""
Automated Retrieval Evaluation Engine for PostgreSQL Lexical Baseline.

Runs benchmark evaluation against the curated 35-query postal evaluation dataset.
Computes:
- Recall@1, Recall@3, Recall@5, Recall@10
- Precision@5
- MRR (Mean Reciprocal Rank)
- nDCG@5 (Normalized Discounted Cumulative Gain with graded relevance)
- Latency statistics (mean, median, min, max ms)
- Query failure and error analysis

Produces: data/postal_documents/evaluation/retrieval_evaluation.json
"""

import sys
import json
import math
import time
import statistics
from pathlib import Path
from typing import Dict, Any, List

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = WORKSPACE_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.postal_retrieval_service import PostalRetrievalService

QUERIES_FILE = WORKSPACE_ROOT / "data" / "postal_documents" / "evaluation" / "retrieval_queries.jsonl"
EVALUATION_OUTPUT = WORKSPACE_ROOT / "data" / "postal_documents" / "evaluation" / "retrieval_evaluation.json"


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


def run_evaluation() -> Dict[str, Any]:
    print(f"Loading evaluation queries from: {QUERIES_FILE}")
    if not QUERIES_FILE.exists():
        raise FileNotFoundError(f"Queries file not found: {QUERIES_FILE}")

    queries = []
    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line.strip()))

    print(f"Loaded {len(queries)} benchmark queries.")

    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    service = PostalRetrievalService(session)

    query_results = []
    recalls = {1: [], 3: [], 5: [], 10: []}
    precisions_5 = []
    reciprocal_ranks = []
    ndcgs_5 = []
    latencies = []
    failed_queries = []

    print("\nExecuting queries against PostgreSQL Native FTS (ts_rank_cd)...")
    for q_idx, q in enumerate(queries, start=1):
        qid = q["query_id"]
        q_text = q["query"]
        expected_ids = set(q["expected_chunk_ids"])
        grades = q.get("relevance_grades", {cid: 2 for cid in expected_ids})

        # Retrieve Top 10 for metrics
        resp = service.search(query=q_text, top_k=10)
        retrieved_ids = [r.chunk_id for r in resp.results]
        latencies.append(resp.latency_ms)

        # 1. Recall @ K
        for k in [1, 3, 5, 10]:
            k_retrieved = set(retrieved_ids[:k])
            # Has at least one primary expected chunk in top K
            hit = 1.0 if any(cid in k_retrieved for cid in expected_ids) else 0.0
            recalls[k].append(hit)

        # 2. Precision @ 5
        top_5 = retrieved_ids[:5]
        relevant_in_top_5 = sum(1 for cid in top_5 if grades.get(cid, 0) > 0)
        p_5 = relevant_in_top_5 / 5.0
        precisions_5.append(p_5)

        # 3. Reciprocal Rank (MRR)
        rr = 0.0
        first_rel_rank = None
        for rank, cid in enumerate(retrieved_ids, start=1):
            if grades.get(cid, 0) > 0:
                rr = 1.0 / rank
                first_rel_rank = rank
                break
        reciprocal_ranks.append(rr)

        # 4. nDCG @ 5
        ndcg_5 = compute_ndcg(retrieved_ids, grades, k=5)
        ndcgs_5.append(ndcg_5)

        is_success = recalls[5][-1] == 1.0
        query_summary = {
            "query_id": qid,
            "query": q_text,
            "category": q["query_category"],
            "difficulty": q["difficulty"],
            "expected_chunk_ids": list(expected_ids),
            "retrieved_chunk_ids": retrieved_ids[:5],
            "recall_at_5": recalls[5][-1],
            "precision_at_5": round(p_5, 3),
            "reciprocal_rank": round(rr, 4),
            "ndcg_at_5": ndcg_5,
            "first_relevant_rank": first_rel_rank,
            "latency_ms": resp.latency_ms,
            "total_matches": resp.total_matches
        }
        query_results.append(query_summary)

        if not is_success:
            failed_queries.append({
                "query_id": qid,
                "query": q_text,
                "category": q["query_category"],
                "expected": list(expected_ids),
                "retrieved_top_5": retrieved_ids[:5],
                "reason": "Expected statutory chunk not retrieved in Top-5 lexical cover density candidates.",
                "total_matches": resp.total_matches
            })

    session.close()

    # Aggregate Metrics
    mean_recall_1 = round(statistics.mean(recalls[1]), 4)
    mean_recall_3 = round(statistics.mean(recalls[3]), 4)
    mean_recall_5 = round(statistics.mean(recalls[5]), 4)
    mean_recall_10 = round(statistics.mean(recalls[10]), 4)
    mean_precision_5 = round(statistics.mean(precisions_5), 4)
    mrr = round(statistics.mean(reciprocal_ranks), 4)
    mean_ndcg_5 = round(statistics.mean(ndcgs_5), 4)

    latency_stats = {
        "count": len(latencies),
        "mean_ms": round(statistics.mean(latencies), 2),
        "median_ms": round(statistics.median(latencies), 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "stdev_ms": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0.0
    }

    report = {
        "benchmark_metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "corpus_chunks": 228,
            "evaluation_queries": len(queries),
            "database_engine": "PostgreSQL 15.8 (Native Full-Text Search)",
            "search_configuration": "english (Snowball stemmer + stopwords)",
            "indexing_method": "GIN (Generalized Inverted Index)",
            "ranking_algorithm": "ts_rank_cd (Cover Density Ranking, normalization=32)",
            "weights": {"A": ["heading", "legal_reference"], "B": ["text"]}
        },
        "aggregate_metrics": {
            "recall_at_1": mean_recall_1,
            "recall_at_3": mean_recall_3,
            "recall_at_5": mean_recall_5,
            "recall_at_10": mean_recall_10,
            "precision_at_5": mean_precision_5,
            "mrr": mrr,
            "ndcg_at_5": mean_ndcg_5
        },
        "latency_statistics": latency_stats,
        "failure_analysis": {
            "total_failed_at_k5": len(failed_queries),
            "failed_queries": failed_queries
        },
        "per_query_results": query_results
    }

    EVALUATION_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(EVALUATION_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n========================================================")
    print(" POSTGRESQL LEXICAL RETRIEVAL BENCHMARK RESULTS")
    print("========================================================")
    print(f" Evaluation Queries : {len(queries)}")
    print(f" Recall@1           : {mean_recall_1 * 100:.2f}%")
    print(f" Recall@3           : {mean_recall_3 * 100:.2f}%")
    print(f" Recall@5           : {mean_recall_5 * 100:.2f}%")
    print(f" Recall@10          : {mean_recall_10 * 100:.2f}%")
    print(f" Precision@5        : {mean_precision_5:.4f}")
    print(f" MRR                : {mrr:.4f}")
    print(f" nDCG@5             : {mean_ndcg_5:.4f}")
    print(f" Latency Mean       : {latency_stats['mean_ms']} ms")
    print(f" Latency Median     : {latency_stats['median_ms']} ms")
    print(f" Latency Range      : [{latency_stats['min_ms']} ms - {latency_stats['max_ms']} ms]")
    print(f" Failed at K=5      : {len(failed_queries)}/{len(queries)}")
    print(f" Output Report Saved: {EVALUATION_OUTPUT}")
    print("========================================================\n")

    return report


if __name__ == "__main__":
    run_evaluation()
