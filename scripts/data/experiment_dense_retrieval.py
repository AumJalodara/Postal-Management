"""
Module 3 Step 4 — Feasibility Experiment Script.

Compares:
Strategy A: Existing PostgreSQL Lexical Retrieval (ts_rank_cd)
Strategy B: Local Dense Semantic Retrieval (all-MiniLM-L6-v2, 384-dim, cosine similarity)
Strategy C: Hybrid Lexical + Dense Reciprocal Rank Fusion (RRF, k=60)

Constraints:
- STRICTLY EXPERIMENTAL (does not alter production code or database schema)
- 100% CPU-only execution
- Offline inference (local_files_only=True)
- Evaluates across all 35 benchmark queries in retrieval_queries.jsonl
- Saves complete data to: data/postal_documents/evaluation/dense_feasibility_experiment.json
"""

import os
import sys
import json
import time
import math
import statistics
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = WORKSPACE_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.postal_retrieval_service import PostalRetrievalService

from sentence_transformers import SentenceTransformer

QUERIES_FILE = WORKSPACE_ROOT / "data" / "postal_documents" / "evaluation" / "retrieval_queries.jsonl"
OUTPUT_FILE = WORKSPACE_ROOT / "data" / "postal_documents" / "evaluation" / "dense_feasibility_experiment.json"
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
RRF_K = 60


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


def load_chunks_from_db(engine) -> List[Dict[str, Any]]:
    """Loads all 228 chunks from postal_document_chunks."""
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT chunk_id, document_title, document_type, section_type,
                   legal_reference, heading, text
            FROM postal_document_chunks
            ORDER BY chunk_id ASC
        """))
        chunks = [dict(row._mapping) for row in result.fetchall()]
    return chunks


def evaluate_strategy(
    strategy_name: str,
    queries: List[Dict[str, Any]],
    ranked_results: List[List[str]],
    latencies_ms: List[float]
) -> Dict[str, Any]:
    """Computes Recall@1/3/5/10, Precision@5, MRR, nDCG@5, and latency metrics."""
    recalls = {1: [], 3: [], 5: [], 10: []}
    precisions_5 = []
    reciprocal_ranks = []
    ndcgs_5 = []
    failed_k5 = []
    per_query = []

    for q, retrieved_ids, lat in zip(queries, ranked_results, latencies_ms):
        qid = q["query_id"]
        expected_ids = set(q["expected_chunk_ids"])
        grades = q.get("relevance_grades", {cid: 2 for cid in expected_ids})

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
                "query": q["query"],
                "expected": list(expected_ids),
                "retrieved_top_5": retrieved_ids[:5],
                "first_relevant_rank": first_rel_rank
            })

        per_query.append({
            "query_id": qid,
            "query": q["query"],
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
            "latency_ms": round(lat, 2)
        })

    metrics = {
        "strategy": strategy_name,
        "recall_at_1": round(statistics.mean(recalls[1]), 4),
        "recall_at_3": round(statistics.mean(recalls[3]), 4),
        "recall_at_5": round(statistics.mean(recalls[5]), 4),
        "recall_at_10": round(statistics.mean(recalls[10]), 4),
        "precision_at_5": round(statistics.mean(precisions_5), 4),
        "mrr": round(statistics.mean(reciprocal_ranks), 4),
        "ndcg_at_5": round(statistics.mean(ndcgs_5), 4),
        "latency_mean_ms": round(statistics.mean(latencies_ms), 2),
        "latency_median_ms": round(statistics.median(latencies_ms), 2),
        "latency_min_ms": round(min(latencies_ms), 2),
        "latency_max_ms": round(max(latencies_ms), 2),
        "total_queries": len(queries),
        "failed_k5_count": len(failed_k5),
        "failed_k5_queries": failed_k5,
        "per_query": per_query
    }
    return metrics


def run_experiment():
    print("=" * 70)
    print(" MODULE 3 STEP 4: DENSE RETRIEVAL FEASIBILITY EXPERIMENT")
    print("=" * 70)

    # 1. Load queries
    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        queries = [json.loads(line) for line in f if line.strip()]
    print(f"Loaded {len(queries)} benchmark queries from: {QUERIES_FILE}")

    # 2. Database connection & chunks
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    chunks = load_chunks_from_db(engine)
    print(f"Loaded {len(chunks)} chunks from PostgreSQL postal_document_chunks table.")
    assert len(chunks) == 228, f"Expected 228 chunks, got {len(chunks)}"

    chunk_ids = [c["chunk_id"] for c in chunks]

    # 3. Model initialization (CPU offline)
    print(f"\nInitializing model: {MODEL_ID} (local_files_only=True)...")
    t0 = time.perf_counter()
    model = SentenceTransformer(MODEL_ID, local_files_only=True)
    load_time = time.perf_counter() - t0
    print(f"Model loaded in {load_time:.2f}s.")
    print(f"  Max sequence length : {model.max_seq_length}")
    print(f"  Tokenizer max length: {model.tokenizer.model_max_length}")
    print(f"  Embedding dimension : {model.get_sentence_embedding_dimension()}")

    # 4. Pre-encode all 228 chunks
    chunk_texts = [f"{c['heading']}. {c['legal_reference']}.\n{c['text']}" for c in chunks]
    print(f"Encoding {len(chunk_texts)} chunks on CPU...")
    t0 = time.perf_counter()
    chunk_embeddings = model.encode(chunk_texts, normalize_embeddings=True, show_progress_bar=False)
    index_time = time.perf_counter() - t0
    print(f"Chunks encoded in {index_time:.2f}s ({index_time/len(chunks)*1000:.1f} ms/chunk).")
    print(f"Embeddings matrix shape: {chunk_embeddings.shape}, dtype: {chunk_embeddings.dtype}")

    # 5. Execute Strategy A: Lexical Baseline
    print("\n[Strategy A] Running PostgreSQL Lexical Baseline...")
    lexical_service = PostalRetrievalService(session)
    lexical_results = []
    lexical_latencies = []

    for q in queries:
        resp = lexical_service.search(query=q["query"], top_k=20)
        retrieved_ids = [r.chunk_id for r in resp.results]
        lexical_results.append(retrieved_ids)
        lexical_latencies.append(resp.latency_ms)

    metrics_lexical = evaluate_strategy("Strategy A: Lexical Baseline (PostgreSQL ts_rank_cd)", queries, lexical_results, lexical_latencies)

    # 6. Execute Strategy B: Dense Semantic Retrieval
    print("[Strategy B] Running Dense Semantic Retrieval (CPU Cosine Similarity)...")
    dense_results = []
    dense_latencies = []

    for q in queries:
        t0 = time.perf_counter()
        q_emb = model.encode(q["query"], normalize_embeddings=True, show_progress_bar=False)
        sims = np.dot(chunk_embeddings, q_emb)
        sorted_indices = np.argsort(sims)[::-1]
        dense_retrieved_ids = [chunk_ids[i] for i in sorted_indices]
        lat = (time.perf_counter() - t0) * 1000.0
        dense_results.append(dense_retrieved_ids)
        dense_latencies.append(lat)

    metrics_dense = evaluate_strategy("Strategy B: Dense Semantic Retrieval (all-MiniLM-L6-v2)", queries, dense_results, dense_latencies)

    # 7. Execute Strategy C: Hybrid RRF Fusion
    print(f"[Strategy C] Running Hybrid Reciprocal Rank Fusion (RRF, k={RRF_K})...")
    hybrid_results = []
    hybrid_latencies = []

    for i, q in enumerate(queries):
        t0 = time.perf_counter()
        lex_list = lexical_results[i]
        dense_list = dense_results[i]

        rrf_scores: Dict[str, float] = {}

        # Lexical rank contribution
        for rank, cid in enumerate(lex_list, start=1):
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (RRF_K + rank))

        # Dense rank contribution (top 50 dense candidates)
        for rank, cid in enumerate(dense_list[:50], start=1):
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (RRF_K + rank))

        # Sort by RRF score descending
        fused = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)
        fused_ids = [cid for cid, score in fused]

        # Total hybrid latency = lexical latency + dense latency + fusion time
        fusion_time_ms = (time.perf_counter() - t0) * 1000.0
        total_hybrid_lat = lexical_latencies[i] + dense_latencies[i] + fusion_time_ms

        hybrid_results.append(fused_ids)
        hybrid_latencies.append(total_hybrid_lat)

    metrics_hybrid = evaluate_strategy(f"Strategy C: Hybrid Lexical + Dense RRF (k={RRF_K})", queries, hybrid_results, hybrid_latencies)

    session.close()

    # 8. Query-by-query comparison and delta analysis
    comparison_table = []
    improved_queries = []
    degraded_queries = []
    unchanged_queries = []

    for idx, q in enumerate(queries):
        qid = q["query_id"]
        expected = q["expected_chunk_ids"]
        
        lex_rank = metrics_lexical["per_query"][idx]["first_relevant_rank"]
        dense_rank = metrics_dense["per_query"][idx]["first_relevant_rank"]
        hybrid_rank = metrics_hybrid["per_query"][idx]["first_relevant_rank"]

        lex_rec5 = metrics_lexical["per_query"][idx]["recall_at_5"]
        hybrid_rec5 = metrics_hybrid["per_query"][idx]["recall_at_5"]

        # Status categorization based on rank and recall@5
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
            "expected_chunk_ids": expected,
            "lexical_rank": lex_rank,
            "dense_rank": dense_rank,
            "hybrid_rank": hybrid_rank,
            "lexical_ndcg5": metrics_lexical["per_query"][idx]["ndcg_at_5"],
            "dense_ndcg5": metrics_dense["per_query"][idx]["ndcg_at_5"],
            "hybrid_ndcg5": metrics_hybrid["per_query"][idx]["ndcg_at_5"],
            "status": status
        })

    # 9. Format output report JSON
    final_report = {
        "metadata": {
            "experiment": "Module 3 Step 4 Feasibility Experiment",
            "model_id": MODEL_ID,
            "model_dimension": 384,
            "max_seq_length": model.max_seq_length,
            "tokenizer_max_length": model.tokenizer.model_max_length,
            "corpus_chunks": len(chunks),
            "benchmark_queries": len(queries),
            "rrf_k": RRF_K,
            "execution_mode": "100% CPU-only, local_files_only=True"
        },
        "summary_table": {
            "metric": ["Recall@1", "Recall@3", "Recall@5", "Recall@10", "Precision@5", "MRR", "nDCG@5", "Median Latency", "Mean Latency", "Top-5 Failures"],
            "strategy_a_lexical": [
                f"{metrics_lexical['recall_at_1']*100:.2f}%",
                f"{metrics_lexical['recall_at_3']*100:.2f}%",
                f"{metrics_lexical['recall_at_5']*100:.2f}%",
                f"{metrics_lexical['recall_at_10']*100:.2f}%",
                f"{metrics_lexical['precision_at_5']:.4f}",
                f"{metrics_lexical['mrr']:.4f}",
                f"{metrics_lexical['ndcg_at_5']:.4f}",
                f"{metrics_lexical['latency_median_ms']:.2f} ms",
                f"{metrics_lexical['latency_mean_ms']:.2f} ms",
                f"{metrics_lexical['failed_k5_count']}/{len(queries)}"
            ],
            "strategy_b_dense": [
                f"{metrics_dense['recall_at_1']*100:.2f}%",
                f"{metrics_dense['recall_at_3']*100:.2f}%",
                f"{metrics_dense['recall_at_5']*100:.2f}%",
                f"{metrics_dense['recall_at_10']*100:.2f}%",
                f"{metrics_dense['precision_at_5']:.4f}",
                f"{metrics_dense['mrr']:.4f}",
                f"{metrics_dense['ndcg_at_5']:.4f}",
                f"{metrics_dense['latency_median_ms']:.2f} ms",
                f"{metrics_dense['latency_mean_ms']:.2f} ms",
                f"{metrics_dense['failed_k5_count']}/{len(queries)}"
            ],
            "strategy_c_hybrid_rrf": [
                f"{metrics_hybrid['recall_at_1']*100:.2f}%",
                f"{metrics_hybrid['recall_at_3']*100:.2f}%",
                f"{metrics_hybrid['recall_at_5']*100:.2f}%",
                f"{metrics_hybrid['recall_at_10']*100:.2f}%",
                f"{metrics_hybrid['precision_at_5']:.4f}",
                f"{metrics_hybrid['mrr']:.4f}",
                f"{metrics_hybrid['ndcg_at_5']:.4f}",
                f"{metrics_hybrid['latency_median_ms']:.2f} ms",
                f"{metrics_hybrid['latency_mean_ms']:.2f} ms",
                f"{metrics_hybrid['failed_k5_count']}/{len(queries)}"
            ]
        },
        "query_deltas": {
            "improved_queries": improved_queries,
            "degraded_queries": degraded_queries,
            "unchanged_queries": unchanged_queries
        },
        "strategies": {
            "strategy_a_lexical": metrics_lexical,
            "strategy_b_dense": metrics_dense,
            "strategy_c_hybrid_rrf": metrics_hybrid
        },
        "comparison_table": comparison_table
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(" COMPARATIVE RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Metric':<20} | {'Lexical Baseline':<16} | {'Dense Only':<16} | {'Hybrid RRF':<16}")
    print("-" * 75)
    for m, l, d, h in zip(
        final_report["summary_table"]["metric"],
        final_report["summary_table"]["strategy_a_lexical"],
        final_report["summary_table"]["strategy_b_dense"],
        final_report["summary_table"]["strategy_c_hybrid_rrf"]
    ):
        print(f"{m:<20} | {l:<16} | {d:<16} | {h:<16}")
    print("=" * 75)
    print(f"\nImproved queries count : {len(improved_queries)}: {improved_queries}")
    print(f"Degraded queries count : {len(degraded_queries)}: {degraded_queries}")
    print(f"Unchanged queries count: {len(unchanged_queries)}: {unchanged_queries}")
    print(f"\nDetailed experiment results saved to: {OUTPUT_FILE}")
    print("=" * 70 + "\n")

    return final_report


if __name__ == "__main__":
    run_experiment()
