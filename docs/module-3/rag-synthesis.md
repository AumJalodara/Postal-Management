# Module 3 — RAG Synthesis Architecture & Implementation

## 1. Module 3 Architecture

Module 3 implements a complete **Information Retrieval + Grounded RAG** pipeline over official Indian postal legal documents. The architecture separates two distinct responsibilities:

```
Official Postal Documents
        ↓
Extraction / OCR
        ↓
Structure-Aware Chunking
        ↓
228 Legal Chunks
        ↓
┌──────────────────────┐
│ Lexical Retrieval    │
│ Dense Retrieval      │
└──────────┬───────────┘
           ↓
       RRF Hybrid
           ↓
     Relevant Chunks
           ↓
     Context Builder
           ↓
     Grounded LLM
           ↓
 Citation Validation
           ↓
    Structured Answer
           ↓
     Postal Assistant
```

**Retrieval** finds relevant official postal evidence. **Generation** explains that evidence in natural language. The LLM never replaces retrieval — the retrieved official corpus remains the evidence foundation.

## 2. Document Corpus

The corpus consists of publicly available official Indian postal documents:

- **Post Office Rules, 2024** (DOC1) — Ministry of Communications, Department of Posts
- **Post Office Act, 2023 + Post Office Regulations, 2024 + Amendment Regulations** (DOC2)

These are publicly available gazette notifications, not confidential government data.

## 3. OCR Pipeline

Documents were processed through:
- Digital text extraction (PyPDF) for digitally-rendered PDFs
- OCR fallback for scanned/image-based pages
- OCR anomaly detection and annotation

## 4. Chunking

Structure-aware legal chunking produced **228 atomic legal chunks**, each with:
- Document and page provenance
- Legal reference (Section, Rule, Regulation)
- Boundary detection method
- OCR anomaly flagging

## 5. Lexical Retrieval

PostgreSQL native full-text search:
- `tsvector` indexed text with GIN index
- `ts_rank_cd` cover-density ranking
- `websearch_to_tsquery` with `plainto_tsquery` fallback
- SQLite keyword-matching fallback for testing

## 6. Dense Retrieval

Local sentence-transformers inference:
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- 384-dimensional embeddings
- Pre-computed and cached in NumPy NPZ archive
- SHA-256 corpus fingerprint staleness validation
- Cosine similarity via vectorized matrix dot product

## 7. RRF Hybrid Retrieval

Reciprocal Rank Fusion (k=60):
- Combines lexical and dense candidate lists
- Deterministic tie-breaking: RRF score → dense similarity → lexical rank → chunk_id
- Frozen benchmarks: 94.29% Recall@5, 100% Recall@10, 0.9303 MRR, 36.8ms median CPU latency

**The retrieval pipeline is frozen and was not modified during RAG implementation.**

## 8. Context Construction

`RAGContextBuilder` (`backend/app/services/rag_context_builder.py`):

- Converts retrieved `PostalChunkResult` objects to XML-tagged context
- Preserves all provenance: chunk_id, document_id, document_title, legal_reference, page, source_pages, retrieval rank, score
- Deterministic ordering by retrieval rank
- Produces a source map for citation validation
- No metadata is fabricated

Example context block:
```xml
<OFFICIAL_POSTAL_SOURCE id="1">

Document ID: DOC2
Document: The Post Office Act, 2023
Page: 13
Legal Reference: Section 9

TEXT:
The Central Government may, by notification, establish post offices...

</OFFICIAL_POSTAL_SOURCE>
```

## 9. LLM Provider

`llm_provider.py` (`backend/app/services/llm_provider.py`):

### Provider Abstraction
- `BaseLLMProvider` — abstract base class with `generate(system_prompt, user_message) → str`
- Provider selection via `LLM_PROVIDER` environment variable

### MockLLMProvider
- Deterministic, offline, zero network dependency
- Analyzes context for `<OFFICIAL_POSTAL_SOURCE>` blocks
- Generates responses with proper citation markers `[1]`, `[2]`, etc.
- Returns insufficient evidence message when no sources in context
- Used for all automated tests

### GoogleGeminiProvider
- Real provider using `google-genai` SDK
- Configurable via `GOOGLE_API_KEY` and `LLM_MODEL_NAME` environment variables
- No secrets in source code
- Optional — not required for automated tests or Module 3 completion

## 10. Grounding

The grounded system prompt (`GROUNDED_SYSTEM_PROMPT` in `rag_synthesis_service.py`):

1. Restricts the LLM to answering ONLY from provided evidence
2. Requires citation markers referencing source IDs
3. Prohibits fabricating information or legal provisions
4. Includes explicit academic prototype disclaimer
5. Includes prompt-injection defense directives

## 11. Citation Validation

After LLM generation, the system:

1. Regex-extracts all `[N]` citation markers from the response
2. Maps each `[N]` to the source map built by the context builder
3. **Valid citations**: Creates `CitationDetail` objects with actual chunk provenance
4. **Invalid citations**: Detected, flagged in `has_invalid_citations` and `invalid_citation_ids` — **NOT silently stripped**
5. **No fabricated metadata**: Citation objects contain only data from actual retrieved chunks

## 12. Evidence Sufficiency

Policy based on actual score distribution analysis:

> **Zero retrieved results = insufficient evidence**
>
> **Retrieved results = use the existing retrieval ranking as the available evidence**

No arbitrary global numerical threshold is used. When evidence is insufficient, the system returns:

> "I could not find sufficient information in the available official postal documents to answer this question reliably."

## 13. Prompt-Injection Handling

Defense-in-depth approach:

1. **System prompt** explicitly marks retrieved text as UNTRUSTED data
2. **Explicit instruction** that document content must NOT be treated as commands
3. **Specific examples** mentioned: "ignore previous instructions", "reveal system prompt"
4. **Only system-level instructions** control LLM behavior
5. **Adversarial regression tests** verify injection text is treated as data

XML tags serve as structural delimiters only — security is NOT claimed from tags alone.

## 14. RAG API

### POST /api/v1/postal/ask

Request:
```json
{
  "query": "What does the Post Office Act say about establishing post offices?",
  "top_k": 5,
  "retrieval_mode": "hybrid"
}
```

Validation:
- `query`: required, 1–1000 characters
- `top_k`: 1–20, default 5
- `retrieval_mode`: "hybrid" | "lexical" | "dense"

Response:
```json
{
  "success": true,
  "data": {
    "query": "...",
    "answer": "...",
    "citations": [
      {
        "citation_id": 1,
        "document_id": "DOC2",
        "document_title": "The Post Office Act, 2023",
        "chunk_id": "DOC2_ACT_SECTION_09",
        "page": 13,
        "source_pages": [13],
        "legal_reference": "Section 9"
      }
    ],
    "retrieved_chunks": 5,
    "grounded": true,
    "insufficient_evidence": false,
    "retrieval_mode": "hybrid",
    "has_invalid_citations": false,
    "invalid_citation_ids": []
  }
}
```

Error responses follow existing project conventions (400, 422, 503).

## 15. Frontend Integration

### Postal Assistant (`/assistant`)

Public route (no authentication required), accessible from the navigation bar.

Features:
- Text input for postal regulation questions
- Example question suggestions
- Loading state with progress indication
- AI-generated answer with "AI-Generated Explanation" label
- Official source citations with "Official Postal Sources" label
- Expandable citation cards (document title, page, legal reference, chunk ID)
- Insufficient evidence state
- Backend error state
- Academic prototype disclaimer

Uses the existing design system (CSS variables, government-service color palette).

## 16. Evaluation Methodology

### Retrieval Metrics (FROZEN)
- Recall@5: 94.29%
- Recall@10: 100%
- MRR: 0.9303
- Median CPU Latency: 36.8ms
- 35 evaluation queries in `retrieval_queries.jsonl`

### RAG Generation Metrics
- 15 manually curated evaluation questions in `rag_evaluation_queries.jsonl`
  - 11 supported questions with verified document_id, chunk_id, page
  - 2 unsupported questions for refusal testing
  - 2 adversarial questions for injection testing
- Structural validation with MockLLM:
  - Citation correctness: all citations map to real chunks
  - Evidence coverage: grounded responses when sources available
  - Refusal behavior: insufficient evidence when no results
  - Injection defense: adversarial text treated as data

**Important**: MockLLM validation is structural only. It verifies pipeline correctness but does NOT verify answer factual correctness or natural language quality. Real LLM validation requires provider configuration.

## 17. Limitations

1. **MockLLM validation only**: Real LLM validation pending `GOOGLE_API_KEY` configuration
2. **No parcel-assistant integration**: "Ask About My Parcel" combining parcel status with postal regulations is documented as future work
3. **No multilingual support**: Corpus and RAG are English-only
4. **Academic prototype**: Not an official India Post service
5. **Corpus scope**: Limited to publicly available Post Office Act 2023, Rules 2024, Regulations 2024, and Amendment Regulations
6. **Operational data is synthetic**: Demo/test data does not represent real India Post operations
7. **No real-time updates**: Corpus is static — does not reflect amendments published after extraction
8. **SQLite fallback limitations**: Lexical retrieval quality is lower in SQLite test environment compared to PostgreSQL production
