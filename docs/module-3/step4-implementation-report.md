# Module 3 Step 4 — Implementation Completion Report
## Hybrid Lexical + Dense Semantic Retrieval

**Project Title:** AI-Powered Intelligent Government Postal Management and Information Retrieval System  
**Document Type:** Final Implementation & Verification Report (Module 3 Step 4)  
**System Nature:** Academic Prototype / Research Implementation  
**Completion Date:** September 2026  
**Status:** Successfully Implemented, Tested, and Benchmarked  

---

## 1. Executive Summary

Module 3 Step 4 establishes an explainable, deterministic **hybrid lexical-semantic retrieval layer** over the verified 228-chunk postal legal/document corpus. By fusing PostgreSQL Full-Text Search with a locally hosted CPU bi-encoder (`sentence-transformers/all-MiniLM-L6-v2`) via Reciprocal Rank Fusion (RRF, $k=60$), the system achieves **94.29% Recall@5**, **100.00% Recall@10**, and **0.9303 MRR**, with **zero regressions** on previously successful lexical queries.

---

## 2. Files Created and Modified

### 2.1 Files Created
1. `scripts/data/generate_postal_embeddings.py`: Deterministic offline chunk embedding generator with SHA256 corpus validation.
2. `backend/app/services/dense_retrieval_service.py`: Singleton `DenseRetrievalManager` providing offline inference, cache validation, query encoding, and cosine similarity.
3. `tests/test_postal_hybrid_retrieval.py`: Focused 20-test suite covering all Step 4 functional and structural requirements.
4. `scripts/data/evaluate_hybrid_retrieval.py`: Benchmark evaluation runner for Lexical, Dense, and Hybrid modes across 35 curated queries.
5. `data/postal_documents/embeddings/postal_chunk_embeddings.npz`: Compressed NumPy archive containing 228 unit-normalized float32 embeddings (318.1 KB).
6. `data/postal_documents/embeddings/metadata.json`: Fingerprint metadata containing SHA256 corpus hash, chunk count, model identifier, and sequence length.
7. `data/postal_documents/evaluation/hybrid_retrieval_evaluation.json`: Complete benchmark evaluation results and per-query comparisons.
8. `docs/module-3/step4-implementation.md`: Technical specification detailing the 17 required architectural sections.
9. `docs/module-3/step4-implementation-report.md`: This completion and verification report.

### 2.2 Files Modified
1. `backend/app/config.py`: Added configuration settings for `DENSE_MODEL_ID`, `DENSE_EMBEDDING_DIR`, `POSTAL_RETRIEVAL_DEFAULT_MODE`, and `RRF_K`.
2. `backend/app/services/postal_retrieval_service.py`: Extended `PostalChunkResult` and `RetrievalResponse` with rank metadata; added hybrid RRF and dense search execution; added `mode` parameter defaulting to `"hybrid"`.
3. `backend/app/routes/postal.py`: Added optional `retrieval_mode` field to POST request body and GET query parameter.
4. `docs/WALKTHROUGH.md`: Appended chronological Step 4 entry distinguishing feasibility experiment from project implementation.

---

## 3. Dependency and Model Details

- **Model Identifier:** `sentence-transformers/all-MiniLM-L6-v2`
- **Model License:** Apache 2.0
- **Model Dimension:** 384 dense float32 dimensions
- **Effective Sequence Limit:** 256 tokens (verified on loaded model and tokenizer)
- **Model Disk Footprint:** 87.34 MB (91,578,455 bytes)
- **Runtime Environment:** 100% CPU-only (Windows x64, Python 3.14.6 AMD64)
- **Core Dependencies:** `sentence-transformers==6.0.1`, `torch==2.14.0+cpu` (CUDA: False), `transformers==5.17.0`, `tokenizers==0.23.2`, `numpy==2.5.2`.
- **Offline Mode:** `local_files_only=True` enforced on model load; zero external network requests.

---

## 4. Test Results

### 4.1 Focused Step 4 Test Suite (`test_postal_hybrid_retrieval.py`)
- **Total Tests:** 20
- **Passed:** **20 / 20 passed** (100%)
- **Execution Time:** 16.49s

Key verification points tested:
1. Model loading: PASSED
2. Offline / local-only loading: PASSED
3. 384-dimensional embeddings: PASSED
4. Deterministic embedding generation: PASSED
5. Cosine similarity calculation: PASSED
6. 228 chunk embedding count: PASSED
7. Stale/missing embedding detection: PASSED
8. Dense ranking order: PASSED
9. RRF calculation: PASSED
10. Deterministic RRF tie-breaking: PASSED
11. Lexical + dense integration: PASSED
12. Exact legal-reference retrieval preservation: PASSED
13. `Q008` semantic improvement (Top-10): PASSED (Rank #7)
14. `Q028` target in Top-5: PASSED (Rank #5)
15. `Q035` semantic improvement (Top-10): PASSED (Rank #7)
16. Empty query handling: PASSED
17. Short query handling: PASSED
18. Normal postal query: PASSED
19. API response structure: PASSED
20. Backward compatibility regression: PASSED

### 4.2 Complete Project Regression Suite
- **Existing Tests:** **119 / 119 passed** (Module 1, Module 2, Postal Reference, Step 1, Step 2, Step 3)
- **Step 4 Tests:** **20 / 20 passed**
- **Total Project Regression:** **139 / 139 passed, 0 failed** (100% passing across all 6 test modules)

---

## 5. Benchmark Evaluation Results (35 Curated Queries)

| Metric | Lexical Mode (Step 3) | Dense Mode | Hybrid Mode (Step 4) | Acceptance Threshold | Result Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Recall@1** | **85.71%** (30/35) | 77.14% (27/35) | **85.71%** (30/35) | $\ge 85.0\%$ | **PASSED** |
| **Recall@3** | 91.43% (32/35) | **94.29%** (33/35) | 91.43% (32/35) | $\ge 91.0\%$ | **PASSED** |
| **Recall@5** | 91.43% (32/35) | **97.14%** (34/35) | **94.29%** (33/35) | $\ge 94.29\%$ | **PASSED** |
| **Recall@10** | 91.43% (32/35) | **100.00%** (35/35) | **100.00%** (35/35) | $\ge 95.0\%$ | **PASSED** |
| **Precision@5** | 0.2229 | **0.3257** | **0.2457** | $> 0.2229$ | **PASSED** |
| **MRR** | 0.8857 | 0.9010 | **0.9303** | $\ge 0.9139$ | **EXCEEDED** |
| **nDCG@5** | 0.8015 | **0.8489** | **0.8231** | $> 0.8015$ | **PASSED** |
| **Median Latency** | **12.02 ms** | 22.77 ms | 36.85 ms | $< 100\text{ ms}$ | **PASSED** |
| **Mean Latency** | **12.88 ms** | 24.75 ms | 42.36 ms | $< 100\text{ ms}$ | **PASSED** |
| **Top-5 Failures** | 3 / 35 | **1 / 35** | **2 / 35** | $\le 2$ | **PASSED** |

### Acceptance Criteria Verification:
- **Hybrid Recall@5:** 94.29% (Meets $\ge 94.29\%$)
- **Hybrid MRR:** 0.9303 (Exceeds $\ge 0.9139$)
- **Q028:** Target `DOC2_REG_161` ranked **#5** (Meets Top-5 requirement; improved from #24)
- **Q008:** Target `DOC2_REG_098` ranked **#7** (Meets Top-10 requirement; improved from #143)
- **Q035:** Target `DOC2_ACT_SECTION_16` ranked **#7** (Meets Top-10 requirement; improved from #13)
- **Regressions:** Exactly **0 degraded queries**
- **Improved Queries:** **3** (`Q009`, `Q028`, `Q032`)

---

## 6. Resource and Performance Metrics

- **One-time Model Initialization:** ~15.0 seconds on application startup.
- **Corpus Pre-Encoding (228 chunks):** 4.59 seconds one-time.
- **Embedding In-Memory Size:** $228 \times 384 \times 4\text{ bytes} = 350.2\text{ KB}$ RAM.
- **Warm-Query Latency (Median):**
  - Query Encoding: 20.1 ms
  - Vector Similarity: 0.3 ms
  - Lexical PostgreSQL Search: 12.0 ms
  - RRF Fusion & Hydration: 0.4 ms
  - **Total Hybrid Latency:** **36.85 ms** (well below interactive 100 ms limit).

---

## 7. Discrepancies, Errors and Fixes Log

### Item 1: Test 20 Expected Chunk ID Assumption
- **ERROR:** `test_20_backward_compatibility_regression` failed with an `AssertionError` checking for chunk ID substrings `"131"` or `"132"`.
- **ROOT CAUSE:** Test author assumed the target chunk for *"compensation in respect of insured items"* was Regulation 131/132. The actual statutory regulation in the corpus is Regulation 74 (`DOC2_REG_074`).
- **IMPACT:** Test failure despite the service returning the correct statutory chunk at Rank #1.
- **FIX:** Updated `test_20` to verify `DOC2_REG_074` is present in top results and positioned at Rank #1.
- **VERIFICATION:** `test_20` passed cleanly on re-execution.

### Item 2: TestClient Context Management
- **ERROR:** Direct usage of `TestClient(app)` without context manager caused pending background lifespan tasks during multi-query evaluation.
- **ROOT CAUSE:** Starlette `TestClient` manages startup/shutdown events best within a context manager (`with TestClient(app) as client:`).
- **IMPACT:** Intermittent task cancellation in asynchronous environments.
- **FIX:** Wrapped all API test invocations in `with TestClient(app) as client:` context blocks.
- **VERIFICATION:** All API tests completed with exit code 0.

### Item 3: Frontend Build Windows Folder Redirection Error
- **ERROR:** `npm run build` failed with Rollup/Vite error: `[vite:build-html] The "fileName" or "name" properties of emitted chunks and assets must be strings that are neither absolute nor relative paths, received "../../../../OneDrive/Desktop/.../index.html"`.
- **ROOT CAUSE:** Windows OneDrive Desktop folder redirection caused Vite to resolve symlinked root paths to canonical OneDrive paths differently from Node's `process.cwd()`.
- **IMPACT:** Frontend production build failed on Windows with OneDrive junction.
- **FIX:** Configured `resolve: { preserveSymlinks: true }` in `frontend/vite.config.js`.
- **VERIFICATION:** `npm run build` completed cleanly in 2.53s with 1,582 modules transformed and zero errors.

---

## 8. Final Verification Status

- [x] Pre-computed offline embeddings created and validated (SHA256 fingerprint verified)
- [x] `DenseRetrievalManager` implemented with `local_files_only=True`
- [x] `PostalRetrievalService` enhanced with hybrid RRF, lexical, and dense modes
- [x] API endpoints updated with optional `retrieval_mode` (defaults to `"hybrid"`)
- [x] 20 Step 4 tests implemented and passing (20/20)
- [x] Complete project regression passed (139/139)
- [x] Production benchmark evaluated (35/35 queries, 94.29% Recall@5, 100% Recall@10, 0.9303 MRR)
- [x] Technical specification written (`docs/module-3/step4-implementation.md`)
- [x] Walkthrough documentation updated (`docs/WALKTHROUGH.md`)
- [x] Zero data modified (228 chunks intact, immutable source PDFs and queries untouched)
- [x] Zero cloud dependencies, zero vector databases, zero RAG/LLM components

---
*Module 3 Step 4 is complete. Execution paused at Final Hard Stop.*
