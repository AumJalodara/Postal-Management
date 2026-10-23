"""
RAG Context Builder for Postal Document Retrieval.

Converts retrieved PostalChunkResult objects into a deterministic,
XML-tagged context string for grounded LLM consumption.

Key design principles:
- Retrieved text is DATA, not instructions to the LLM
- All provenance metadata comes from actual retrieval results
- No metadata is fabricated
- Deterministic ordering by retrieval rank
- Source map enables citation validation after LLM generation
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("smart_postal.rag_context")


class RAGContextBuilder:
    """
    Builds structured context from retrieved postal document chunks
    for grounded LLM consumption.
    """

    def build_context(
        self,
        retrieved_results: List[Any],
    ) -> tuple:
        """
        Builds an XML-tagged context string and source map from retrieved results.

        Args:
            retrieved_results: List of PostalChunkResult objects from the retrieval service,
                               already ordered by retrieval rank.

        Returns:
            Tuple of (context_string, source_map)
            - context_string: XML-tagged string with all retrieved sources
            - source_map: Dict mapping citation_id (1-indexed) to chunk metadata
        """
        if not retrieved_results:
            return "", {}

        context_parts = []
        source_map: Dict[int, Dict[str, Any]] = {}

        for idx, result in enumerate(retrieved_results, start=1):
            # Extract provenance directly from the retrieval result
            chunk_id = result.chunk_id
            document_title = result.document_title
            legal_reference = result.legal_reference
            start_page = result.start_page
            source_pages = result.source_pages
            text = result.text
            relevance_score = result.relevance_score
            retrieval_mode = getattr(result, "retrieval_mode", None)
            clean_text = getattr(result, "clean_text", None)
            heading = getattr(result, "heading", None)
            ocr_anomaly = getattr(result, "ocr_anomaly", False)
            anomaly_note = getattr(result, "anomaly_note", None)

            # Extract document_id from chunk_id (e.g., "DOC1_RULE_02" -> "DOC1")
            # The chunk_id format is DOC{N}_{type}_{number}
            document_id = self._extract_document_id(chunk_id)

            # Build the XML-tagged source block with clean text when available
            effective_text = clean_text if clean_text else text
            source_block = self._format_source_block(
                citation_id=idx,
                document_id=document_id,
                document_title=document_title,
                start_page=start_page,
                source_pages=source_pages,
                legal_reference=legal_reference,
                text=effective_text,
                retrieval_rank=idx,
                relevance_score=relevance_score,
                heading=heading,
            )
            context_parts.append(source_block)

            # Build source map entry for citation validation
            source_map[idx] = {
                "citation_id": idx,
                "chunk_id": chunk_id,
                "document_id": document_id,
                "document_title": document_title,
                "legal_reference": legal_reference,
                "heading": heading,
                "page": start_page,
                "source_pages": source_pages if isinstance(source_pages, list) else [start_page],
                "retrieval_rank": idx,
                "relevance_score": float(relevance_score),
                "retrieval_mode": retrieval_mode,
                "text": text,
                "clean_text": clean_text,
                "ocr_anomaly": ocr_anomaly,
                "anomaly_note": anomaly_note,
            }

        context_string = "\n\n".join(context_parts)

        logger.info(
            f"Built RAG context with {len(source_map)} sources "
            f"({len(context_string)} chars)"
        )

        return context_string, source_map

    def _extract_document_id(self, chunk_id: str) -> str:
        """
        Extracts the document ID prefix from a chunk_id.

        Chunk IDs follow the pattern: DOC{N}_{section_type}_{number}
        e.g., 'DOC1_RULE_02' -> 'DOC1', 'DOC2_ACT_SECTION_09' -> 'DOC2'
        """
        if not chunk_id:
            return "UNKNOWN"

        parts = chunk_id.split("_")
        if parts and parts[0].startswith("DOC"):
            return parts[0]
        return "UNKNOWN"

    def _format_source_block(
        self,
        citation_id: int,
        document_id: str,
        document_title: str,
        start_page: int,
        source_pages: Any,
        legal_reference: str,
        text: str,
        retrieval_rank: int,
        relevance_score: float,
        heading: Optional[str] = None,
    ) -> str:
        """
        Formats a single retrieved chunk as an XML-tagged source block.

        The XML tags serve as structural delimiters for the LLM to identify
        source boundaries. They do NOT provide security — prompt injection
        defense is handled separately in the system prompt.
        """
        pages_str = ", ".join(str(p) for p in source_pages) if isinstance(source_pages, list) else str(start_page)
        heading_line = f"Heading: {heading}\n" if heading else ""

        return (
            f'<OFFICIAL_POSTAL_SOURCE id="{citation_id}">\n'
            f"\n"
            f"Document ID: {document_id}\n"
            f"Document: {document_title}\n"
            f"Page: {start_page}\n"
            f"Source Pages: {pages_str}\n"
            f"Legal Reference: {legal_reference}\n"
            f"{heading_line}"
            f"Retrieval Rank: {retrieval_rank}\n"
            f"Relevance Score: {relevance_score}\n"
            f"\n"
            f"TEXT:\n"
            f"{text}\n"
            f"\n"
            f"</OFFICIAL_POSTAL_SOURCE>"
        )
