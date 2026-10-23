"""
Postal Retrieval Service.

Implements Hybrid Lexical + Dense Semantic Retrieval over the 228 verified postal legal chunks:
1. PostgreSQL Native Lexical Retrieval (tsvector, GIN index, and ts_rank_cd cover-density ranking)
2. Local Dense Semantic Retrieval (all-MiniLM-L6-v2 384-dimensional embeddings, cosine similarity)
3. Reciprocal Rank Fusion (RRF, k=60) with deterministic tie-breaking.

Supports retrieval modes: 'hybrid' (default), 'lexical', 'dense'.
Maintains backward compatibility with Step 3 API contracts and test suites.
"""

import time
import logging
import re
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text, func, select

from app.config import settings
from app.models.postal_chunk import PostalDocumentChunk
from app.services.dense_retrieval_service import DenseRetrievalManager
from app.services.postal_statutory_text import get_clean_statutory_info

logger = logging.getLogger("smart_postal.retrieval")

MAX_QUERY_LENGTH = 500
MIN_TOP_K = 1
MAX_TOP_K = 20
DEFAULT_TOP_K = 5
DEFAULT_RRF_K = 60


class PostalChunkResult(BaseModel):
    chunk_id: str
    legal_reference: str
    heading: str
    document_title: str
    document_type: str
    section_type: str
    start_page: int
    end_page: int
    source_pages: List[int]
    relevance_score: float
    text: str
    ocr_anomaly: bool
    anomaly_note: Optional[str] = None
    lexical_rank: Optional[int] = None
    dense_rank: Optional[int] = None
    lexical_score: Optional[float] = None
    dense_similarity: Optional[float] = None
    retrieval_mode: Optional[str] = None
    clean_text: Optional[str] = None


def extract_statutory_target(query: str) -> Optional[Dict[str, Any]]:
    """
    Extracts statutory target (section, rule, regulation, schedule) and number from query.
    e.g. 'What does Section 9 of the Post Office Act say?'
    -> {'unit_type': 'section', 'unit_number': 9, 'doc_hint': 'Act'}
    """
    if not query:
        return None

    q_lower = query.lower()

    # Determine doc hint if mentioned
    doc_hint = None
    if "act" in q_lower:
        doc_hint = "Act"
    elif "rule" in q_lower and "section" not in q_lower:
        doc_hint = "Rules"
    elif "regulation" in q_lower or "reg" in q_lower:
        doc_hint = "Regulations"

    # Match Section
    m_sec = re.search(r'\b(?:section|sec)\.?\s*(\d+)\b', q_lower)
    if m_sec:
        return {
            "unit_type": "section",
            "unit_number": int(m_sec.group(1)),
            "doc_hint": doc_hint or "Act"
        }

    # Match Rule
    m_rule = re.search(r'\brule\.?\s*(\d+)\b', q_lower)
    if m_rule:
        return {
            "unit_type": "rule",
            "unit_number": int(m_rule.group(1)),
            "doc_hint": doc_hint or "Rules"
        }

    # Match Regulation
    m_reg = re.search(r'\b(?:regulation|reg)\.?\s*(\d+)\b', q_lower)
    if m_reg:
        return {
            "unit_type": "regulation",
            "unit_number": int(m_reg.group(1)),
            "doc_hint": doc_hint or "Regulations"
        }

    # Match Schedule
    m_sched = re.search(r'\bschedule\.?\s*([ivx]+|\d+)\b', q_lower)
    if m_sched:
        return {
            "unit_type": "schedule",
            "unit_number": m_sched.group(1),
            "doc_hint": doc_hint or "Regulations"
        }

    return None


def is_chunk_match_target(chunk_id: str, legal_reference: str, heading: str, target: Dict[str, Any]) -> bool:
    """Checks whether a chunk matches the extracted statutory target."""
    if not target:
        return False
    u_type = target.get("unit_type")
    u_num = target.get("unit_number")

    if u_type == "section" and isinstance(u_num, int):
        expected_cid = f"DOC2_ACT_SECTION_{u_num:02d}"
        if chunk_id == expected_cid:
            return True
        ref_lower = (legal_reference or "").lower()
        if f"section {u_num}" in ref_lower:
            return True

    elif u_type == "rule" and isinstance(u_num, int):
        expected_cid = f"DOC1_RULE_{u_num:02d}"
        if chunk_id == expected_cid:
            return True
        ref_lower = (legal_reference or "").lower()
        if f"rule {u_num}" in ref_lower:
            return True

    elif u_type == "regulation" and isinstance(u_num, int):
        expected_cid = f"DOC2_REG_{u_num:03d}"
        if chunk_id == expected_cid:
            return True
        ref_lower = (legal_reference or "").lower()
        if f"regulation {u_num}" in ref_lower or f"reg {u_num}" in ref_lower:
            return True

    elif u_type == "schedule":
        ref_lower = (legal_reference or "").lower()
        if f"schedule {u_num}" in ref_lower:
            return True
        if str(u_num).lower() in chunk_id.lower():
            return True

    return False


def build_postal_chunk_result(
    chunk_id: str,
    legal_reference: str,
    heading: str,
    document_title: str,
    document_type: str,
    section_type: str,
    start_page: int,
    end_page: int,
    source_pages: List[int],
    relevance_score: float,
    text: str,
    ocr_anomaly: bool,
    anomaly_note: Optional[str] = None,
    lexical_rank: Optional[int] = None,
    dense_rank: Optional[int] = None,
    lexical_score: Optional[float] = None,
    dense_similarity: Optional[float] = None,
    retrieval_mode: Optional[str] = None
) -> PostalChunkResult:
    """Builds a PostalChunkResult, hydrating clean statutory text and heading if available."""
    clean_info = get_clean_statutory_info(chunk_id)
    final_heading = clean_info[0] if clean_info else heading
    clean_text = clean_info[1] if clean_info else None

    return PostalChunkResult(
        chunk_id=chunk_id,
        legal_reference=legal_reference,
        heading=final_heading,
        document_title=document_title,
        document_type=document_type,
        section_type=section_type,
        start_page=start_page,
        end_page=end_page,
        source_pages=source_pages,
        relevance_score=relevance_score,
        text=text,
        ocr_anomaly=ocr_anomaly,
        anomaly_note=anomaly_note,
        lexical_rank=lexical_rank,
        dense_rank=dense_rank,
        lexical_score=lexical_score,
        dense_similarity=dense_similarity,
        retrieval_mode=retrieval_mode,
        clean_text=clean_text
    )


class RetrievalResponse(BaseModel):
    query: str
    total_matches: int
    top_k: int
    latency_ms: float
    retrieval_mode: str = "hybrid"
    results: List[PostalChunkResult]


class PostalRetrievalService:
    """
    Unified Postal Retrieval Service supporting Lexical, Dense, and Hybrid (RRF) retrieval.
    """

    def __init__(self, db: Session):
        self.db = db
        self.rrf_k = getattr(settings, "RRF_K", DEFAULT_RRF_K)

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        document_type: Optional[str] = None,
        section_type: Optional[str] = None,
        document_id: Optional[str] = None,
        mode: Optional[str] = None
    ) -> RetrievalResponse:
        start_time = time.perf_counter()

        # 1. Input validation and sanitation
        if query is None:
            clean_query = ""
        else:
            clean_query = str(query).strip()

        # Truncate if exceeds max length
        if len(clean_query) > MAX_QUERY_LENGTH:
            clean_query = clean_query[:MAX_QUERY_LENGTH]

        # Enforce top_k boundaries
        effective_top_k = max(MIN_TOP_K, min(top_k, MAX_TOP_K))

        # Determine retrieval mode (defaults to hybrid if not specified)
        if mode is None:
            effective_mode = getattr(settings, "POSTAL_RETRIEVAL_DEFAULT_MODE", "hybrid").lower()
        else:
            effective_mode = str(mode).strip().lower()

        if effective_mode not in ["hybrid", "lexical", "dense"]:
            raise ValueError(f"Invalid retrieval mode '{mode}'. Must be 'hybrid', 'lexical', or 'dense'.")

        # Safe handling of empty or blank queries
        if not clean_query:
            latency = (time.perf_counter() - start_time) * 1000.0
            return RetrievalResponse(
                query="",
                total_matches=0,
                top_k=effective_top_k,
                latency_ms=round(latency, 2),
                retrieval_mode=effective_mode,
                results=[]
            )

        # 2. Dispatch based on mode
        if effective_mode == "lexical":
            results, total_matches = self._execute_lexical_search(
                clean_query=clean_query,
                top_k=effective_top_k,
                document_type=document_type,
                section_type=section_type,
                document_id=document_id
            )
            for idx, r in enumerate(results, start=1):
                r.lexical_rank = idx
                r.lexical_score = r.relevance_score
                r.retrieval_mode = "lexical"

        elif effective_mode == "dense":
            results, total_matches = self._execute_dense_search(
                clean_query=clean_query,
                top_k=effective_top_k,
                document_type=document_type,
                section_type=section_type,
                document_id=document_id
            )

        else:  # hybrid
            results, total_matches = self._execute_hybrid_search(
                clean_query=clean_query,
                top_k=effective_top_k,
                document_type=document_type,
                section_type=section_type,
                document_id=document_id
            )

        latency = (time.perf_counter() - start_time) * 1000.0
        return RetrievalResponse(
            query=clean_query,
            total_matches=total_matches,
            top_k=effective_top_k,
            latency_ms=round(latency, 2),
            retrieval_mode=effective_mode,
            results=results
        )

    def _execute_lexical_search(
        self,
        clean_query: str,
        top_k: int,
        document_type: Optional[str] = None,
        section_type: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> Tuple[List[PostalChunkResult], int]:
        """Dispatches lexical search to PostgreSQL or SQLite fallback."""
        bind = self.db.get_bind()
        is_postgres = bind.dialect.name == "postgresql"
        if is_postgres:
            return self._search_postgresql(
                clean_query=clean_query,
                top_k=top_k,
                document_type=document_type,
                section_type=section_type,
                document_id=document_id
            )
        else:
            return self._search_sqlite_fallback(
                clean_query=clean_query,
                top_k=top_k,
                document_type=document_type,
                section_type=section_type,
                document_id=document_id
            )

    def _execute_dense_search(
        self,
        clean_query: str,
        top_k: int,
        document_type: Optional[str] = None,
        section_type: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> Tuple[List[PostalChunkResult], int]:
        """Executes pure dense semantic retrieval with fallback to lexical if unavailable."""
        dense_mgr = DenseRetrievalManager.get_instance()
        if not dense_mgr.is_available:
            logger.warning(
                f"Dense retrieval is unavailable ({dense_mgr.error_reason}); "
                f"falling back to lexical search for dense mode."
            )
            lex_results, total = self._execute_lexical_search(
                clean_query=clean_query,
                top_k=top_k,
                document_type=document_type,
                section_type=section_type,
                document_id=document_id
            )
            for r in lex_results:
                r.retrieval_mode = "dense_fallback"
            return lex_results, total

        dense_candidates, _, _ = dense_mgr.search(clean_query, top_k=228)

        # Apply metadata filters if specified
        valid_chunk_ids = self._get_filtered_chunk_ids(document_type, section_type, document_id)
        if valid_chunk_ids is not None:
            dense_candidates = [c for c in dense_candidates if c[0] in valid_chunk_ids]

        total_matches = len(dense_candidates)
        top_candidates = dense_candidates[:top_k]
        if not top_candidates:
            return [], 0

        target_ids = [cid for cid, sim, rank in top_candidates]
        chunks_map = self._hydrate_chunks(target_ids)

        results = []
        for rank, (cid, sim, _) in enumerate(top_candidates, start=1):
            chunk = chunks_map.get(cid)
            if chunk:
                pages = chunk.source_pages
                if not isinstance(pages, list):
                    pages = list(pages) if pages is not None else [chunk.start_page]

                results.append(build_postal_chunk_result(
                    chunk_id=chunk.chunk_id,
                    legal_reference=chunk.legal_reference,
                    heading=chunk.heading,
                    document_title=chunk.document_title,
                    document_type=chunk.document_type,
                    section_type=chunk.section_type,
                    start_page=chunk.start_page,
                    end_page=chunk.end_page,
                    source_pages=pages,
                    relevance_score=float(sim),
                    text=chunk.text,
                    ocr_anomaly=chunk.ocr_anomaly,
                    anomaly_note=chunk.anomaly_note,
                    dense_rank=rank,
                    dense_similarity=float(sim),
                    retrieval_mode="dense"
                ))

        return results, total_matches

    def _execute_hybrid_search(
        self,
        clean_query: str,
        top_k: int,
        document_type: Optional[str] = None,
        section_type: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> Tuple[List[PostalChunkResult], int]:
        """
        Executes Reciprocal Rank Fusion (RRF, k=60) combining PostgreSQL Lexical and Dense retrieval.
        Degrades gracefully to lexical if dense embeddings are missing.
        """
        dense_mgr = DenseRetrievalManager.get_instance()
        if not dense_mgr.is_available:
            logger.warning(
                f"Dense retrieval is unavailable ({dense_mgr.error_reason}); "
                f"gracefully falling back to cover-density lexical search for hybrid query."
            )
            lex_results, total = self._execute_lexical_search(
                clean_query=clean_query,
                top_k=top_k,
                document_type=document_type,
                section_type=section_type,
                document_id=document_id
            )
            for r in lex_results:
                r.retrieval_mode = "hybrid_fallback"
            return lex_results, total

        # 1. Lexical retrieval candidate retrieval (up to top 20 candidates)
        lexical_results, _ = self._execute_lexical_search(
            clean_query=clean_query,
            top_k=20,
            document_type=document_type,
            section_type=section_type,
            document_id=document_id
        )

        lexical_map: Dict[str, Tuple[int, float, PostalChunkResult]] = {}
        for rank, res in enumerate(lexical_results, start=1):
            lexical_map[res.chunk_id] = (rank, res.relevance_score, res)

        # 2. Dense semantic retrieval (full 228 chunk candidate pool to ensure statutory exact matches are never pruned)
        dense_candidates, _, _ = dense_mgr.search(clean_query, top_k=228)

        # Filter dense candidates if metadata filters are active
        valid_chunk_ids = self._get_filtered_chunk_ids(document_type, section_type, document_id)
        if valid_chunk_ids is not None:
            dense_candidates = [c for c in dense_candidates if c[0] in valid_chunk_ids]

        dense_map: Dict[str, Tuple[int, float]] = {}
        for rank, (cid, sim, _) in enumerate(dense_candidates, start=1):
            dense_map[cid] = (rank, sim)

        # 3. Reciprocal Rank Fusion calculation with Statutory Target Awareness
        statutory_target = extract_statutory_target(clean_query)
        all_chunk_ids = set(lexical_map.keys()).union(set(dense_map.keys()))
        if not all_chunk_ids:
            return [], 0

        fused_scores: List[Dict[str, Any]] = []
        for cid in all_chunk_ids:
            rrf_score = 0.0
            lex_rank = None
            lex_score = None
            lex_ref = ""
            lex_heading = ""
            if cid in lexical_map:
                lex_rank, lex_score, lex_obj = lexical_map[cid]
                lex_ref = lex_obj.legal_reference
                lex_heading = lex_obj.heading
                rrf_score += 1.0 / (self.rrf_k + lex_rank)

            dense_rank = None
            dense_sim = 0.0
            if cid in dense_map:
                dense_rank, dense_sim = dense_map[cid]
                rrf_score += 1.0 / (self.rrf_k + dense_rank)

            # Statutory exact target boost (e.g. user asks for Section 9 -> boost Section 9 chunk)
            if statutory_target and is_chunk_match_target(cid, lex_ref, lex_heading, statutory_target):
                rrf_score += 0.05

            fused_scores.append({
                "chunk_id": cid,
                "rrf_score": rrf_score,
                "lexical_rank": lex_rank,
                "lexical_score": lex_score,
                "dense_rank": dense_rank,
                "dense_similarity": dense_sim
            })

        # 4. Deterministic sorting:
        # Primary: rrf_score descending
        # Secondary: lexical_rank ascending (None -> 999999)
        # Tertiary: dense_similarity descending
        # Quaternary: chunk_id ascending
        fused_scores.sort(
            key=lambda x: (
                -x["rrf_score"],
                x["lexical_rank"] if x["lexical_rank"] is not None else 999999,
                -x["dense_similarity"],
                x["chunk_id"]
            )
        )

        total_matches = len(fused_scores)
        top_fused = fused_scores[:top_k]

        # 5. Hydrate missing chunk metadata (if not already fetched during lexical search)
        needed_hydrate_ids = [item["chunk_id"] for item in top_fused if item["chunk_id"] not in lexical_map]
        hydrated_map = self._hydrate_chunks(needed_hydrate_ids) if needed_hydrate_ids else {}

        # 6. Assemble final PostalChunkResult objects
        results = []
        for item in top_fused:
            cid = item["chunk_id"]
            if cid in lexical_map:
                base = lexical_map[cid][2]
                results.append(build_postal_chunk_result(
                    chunk_id=base.chunk_id,
                    legal_reference=base.legal_reference,
                    heading=base.heading,
                    document_title=base.document_title,
                    document_type=base.document_type,
                    section_type=base.section_type,
                    start_page=base.start_page,
                    end_page=base.end_page,
                    source_pages=base.source_pages,
                    relevance_score=round(float(item["rrf_score"]), 5),
                    text=base.text,
                    ocr_anomaly=base.ocr_anomaly,
                    anomaly_note=base.anomaly_note,
                    lexical_rank=item["lexical_rank"],
                    dense_rank=item["dense_rank"],
                    lexical_score=item["lexical_score"],
                    dense_similarity=round(float(item["dense_similarity"]), 5) if item["dense_rank"] is not None else None,
                    retrieval_mode="hybrid"
                ))
            else:
                chunk = hydrated_map.get(cid)
                if chunk:
                    pages = chunk.source_pages
                    if not isinstance(pages, list):
                        pages = list(pages) if pages is not None else [chunk.start_page]
                    results.append(build_postal_chunk_result(
                        chunk_id=chunk.chunk_id,
                        legal_reference=chunk.legal_reference,
                        heading=chunk.heading,
                        document_title=chunk.document_title,
                        document_type=chunk.document_type,
                        section_type=chunk.section_type,
                        start_page=chunk.start_page,
                        end_page=chunk.end_page,
                        source_pages=pages,
                        relevance_score=round(float(item["rrf_score"]), 5),
                        text=chunk.text,
                        ocr_anomaly=chunk.ocr_anomaly,
                        anomaly_note=chunk.anomaly_note,
                        lexical_rank=item["lexical_rank"],
                        dense_rank=item["dense_rank"],
                        lexical_score=item["lexical_score"],
                        dense_similarity=round(float(item["dense_similarity"]), 5) if item["dense_rank"] is not None else None,
                        retrieval_mode="hybrid"
                    ))

        return results, total_matches

    def _get_filtered_chunk_ids(
        self,
        document_type: Optional[str],
        section_type: Optional[str],
        document_id: Optional[str]
    ) -> Optional[set]:
        """Returns set of matching chunk_ids if filters are present, or None if no filters."""
        if not document_type and not section_type and not document_id:
            return None

        q = select(PostalDocumentChunk.chunk_id)
        if document_type:
            q = q.where(PostalDocumentChunk.document_type == document_type)
        if section_type:
            q = q.where(PostalDocumentChunk.section_type == section_type)
        if document_id:
            q = q.where(PostalDocumentChunk.document_id == document_id)

        rows = self.db.scalars(q).all()
        return set(rows)

    def _hydrate_chunks(self, chunk_ids: List[str]) -> Dict[str, PostalDocumentChunk]:
        """Fetches full PostalDocumentChunk records by chunk_ids."""
        if not chunk_ids:
            return {}
        q = select(PostalDocumentChunk).where(PostalDocumentChunk.chunk_id.in_(chunk_ids))
        chunks = self.db.scalars(q).all()
        return {c.chunk_id: c for c in chunks}

    def _search_postgresql(
        self,
        clean_query: str,
        top_k: int,
        document_type: Optional[str] = None,
        section_type: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> Tuple[List[PostalChunkResult], int]:
        """
        Execute PostgreSQL native lexical search using websearch_to_tsquery + ts_rank_cd.
        """
        filter_clauses = [
            "((q.strict_q IS NOT NULL AND c.search_vector @@ q.strict_q) OR (q.or_q IS NOT NULL AND c.search_vector @@ q.or_q))"
        ]
        params: Dict[str, Any] = {"raw_query": clean_query, "top_k": top_k}

        if document_type:
            filter_clauses.append("c.document_type = :document_type")
            params["document_type"] = document_type
        if section_type:
            filter_clauses.append("c.section_type = :section_type")
            params["section_type"] = section_type
        if document_id:
            filter_clauses.append("c.document_id = :document_id")
            params["document_id"] = document_id

        where_sql = " AND ".join(filter_clauses)

        query_sql = f"""
            WITH query_prep AS (
                SELECT 
                    websearch_to_tsquery('english', :raw_query) AS strict_q,
                    to_tsquery('english', (
                        SELECT string_agg(lexeme, ' | ')
                        FROM unnest(to_tsvector('english', :raw_query))
                    )) AS or_q
            )
            SELECT 
                c.chunk_id,
                c.legal_reference,
                c.heading,
                c.document_title,
                c.document_type,
                c.section_type,
                c.start_page,
                c.end_page,
                c.source_pages,
                round((
                    CASE 
                        WHEN q.strict_q IS NOT NULL AND c.search_vector @@ q.strict_q THEN 1.0 
                        ELSE 0.0 
                    END 
                    + ts_rank_cd(c.search_vector, coalesce(q.strict_q, q.or_q), 32)
                )::numeric, 5) AS relevance_score,
                c.text,
                c.ocr_anomaly,
                c.anomaly_note,
                count(*) OVER() AS total_count
            FROM postal_document_chunks c, query_prep q
            WHERE {where_sql}
            ORDER BY relevance_score DESC, c.chunk_id ASC
            LIMIT :top_k;
        """

        try:
            rows = self.db.execute(text(query_sql), params).fetchall()
        except Exception as err:
            logger.warning(f"websearch_to_tsquery failed, falling back to plainto_tsquery: {err}")
            fallback_sql = query_sql.replace("websearch_to_tsquery", "plainto_tsquery")
            rows = self.db.execute(text(fallback_sql), params).fetchall()

        results = []
        total_count = 0
        for r in rows:
            total_count = r[13]
            pages = r[8]
            if not isinstance(pages, list):
                pages = list(pages) if pages is not None else [r[6]]

            results.append(build_postal_chunk_result(
                chunk_id=r[0],
                legal_reference=r[1],
                heading=r[2],
                document_title=r[3],
                document_type=r[4],
                section_type=r[5],
                start_page=r[6],
                end_page=r[7],
                source_pages=pages,
                relevance_score=float(r[9]),
                text=r[10],
                ocr_anomaly=bool(r[11]),
                anomaly_note=r[12]
            ))

        return results, total_count

    def _search_sqlite_fallback(
        self,
        clean_query: str,
        top_k: int,
        document_type: Optional[str] = None,
        section_type: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> Tuple[List[PostalChunkResult], int]:
        """
        Lightweight fallback search for SQLite test runner.
        Performs keyword matching over heading, reference, and text with statutory target boosting.
        """
        import re
        q_lower = clean_query.lower()
        words = [w for w in re.findall(r"\w+", q_lower) if len(w) > 0]
        if not words:
            return [], 0

        query = select(PostalDocumentChunk)
        if document_type:
            query = query.where(PostalDocumentChunk.document_type == document_type)
        if section_type:
            query = query.where(PostalDocumentChunk.section_type == section_type)
        if document_id:
            query = query.where(PostalDocumentChunk.document_id == document_id)

        all_chunks = self.db.scalars(query).all()
        statutory_target = extract_statutory_target(clean_query)
        scored = []
        for c in all_chunks:
            haystack_heading = (c.heading or "").lower()
            haystack_ref = (c.legal_reference or "").lower()
            haystack_text = (c.text or "").lower()

            h_tokens = set(re.findall(r"\w+", haystack_heading))
            r_tokens = set(re.findall(r"\w+", haystack_ref))
            t_tokens = set(re.findall(r"\w+", haystack_text))
            all_head_tokens = h_tokens | r_tokens

            score = 0.0

            # Statutory target exact match boost
            if statutory_target and is_chunk_match_target(c.chunk_id, c.legal_reference, c.heading, statutory_target):
                score += 35.0
                if statutory_target.get("doc_hint") and statutory_target["doc_hint"].lower() in (c.document_title or "").lower():
                    score += 15.0

            if q_lower in haystack_heading or q_lower in haystack_ref:
                score += 15.0
            elif q_lower in haystack_text:
                score += 8.0

            matched_words = 0
            for w in words:
                if w in all_head_tokens:
                    score += 3.0
                    matched_words += 1
                elif w in t_tokens:
                    score += 1.0
                    matched_words += 1

            if score > 0:
                final_score = round(score / (score + 5.0), 5)
                scored.append((c, final_score))

        scored.sort(key=lambda x: (-x[1], x[0].chunk_id))
        total_matches = len(scored)
        top_items = scored[:top_k]

        results = []
        for c, s in top_items:
            pages = c.source_pages
            if not isinstance(pages, list):
                pages = list(pages) if pages is not None else [c.start_page]
            results.append(build_postal_chunk_result(
                chunk_id=c.chunk_id,
                legal_reference=c.legal_reference,
                heading=c.heading,
                document_title=c.document_title,
                document_type=c.document_type,
                section_type=c.section_type,
                start_page=c.start_page,
                end_page=c.end_page,
                source_pages=pages,
                relevance_score=s,
                text=c.text,
                ocr_anomaly=c.ocr_anomaly,
                anomaly_note=c.anomaly_note
            ))

        return results, total_matches
