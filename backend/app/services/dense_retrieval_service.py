"""
Dense Semantic Retrieval Service for Postal Document Chunks.

Manages local offline inference using sentence-transformers/all-MiniLM-L6-v2.
Loads pre-computed 384-dimensional chunk embeddings from a deterministic NumPy archive.
Validates cache staleness against the cryptographic corpus SHA256 fingerprint.
Computes cosine similarity on CPU via vectorized matrix dot product.
Provides deterministic ranking with clear error reporting if the local model or cache is missing.
"""

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

from app.config import settings

logger = logging.getLogger("smart_postal.dense_retrieval")

EXPECTED_CHUNK_COUNT = 228
EXPECTED_DIM = 384
EXPECTED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
EXPECTED_PREPROCESSING_VERSION = "1.0.0"


class DenseRetrievalManager:
    """
    Singleton manager for local dense semantic retrieval over postal document chunks.
    """
    _instance: Optional["DenseRetrievalManager"] = None

    def __init__(self):
        self.embedding_dir = Path(settings.DENSE_EMBEDDING_DIR)
        self.npz_path = self.embedding_dir / "postal_chunk_embeddings.npz"
        self.metadata_path = self.embedding_dir / "metadata.json"
        self.model_id = settings.DENSE_MODEL_ID

        self.model = None
        self.chunk_ids: Optional[np.ndarray] = None
        self.embeddings: Optional[np.ndarray] = None
        self.metadata: Optional[Dict[str, Any]] = None
        self.model_load_time_ms: float = 0.0
        self.is_available: bool = False
        self.error_reason: Optional[str] = None

        self._initialize()

    @classmethod
    def get_instance(cls) -> "DenseRetrievalManager":
        """Access or instantiate the global singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing or cache reloads)."""
        cls._instance = None

    def _initialize(self):
        """Initializes model and validates embedding cache with graceful fallback."""
        t0 = time.perf_counter()
        try:
            # 1. Validate Cache
            self._validate_and_load_cache()

            # 2. Load Local Model (local_files_only=True)
            self._load_local_model()

            self.model_load_time_ms = (time.perf_counter() - t0) * 1000.0
            self.is_available = True
            self.error_reason = None
            logger.info(
                f"DenseRetrievalManager initialized in {self.model_load_time_ms:.1f} ms "
                f"({len(self.chunk_ids)} chunks, dim={self.embeddings.shape[1]})."
            )
        except Exception as err:
            self.is_available = False
            self.error_reason = str(err)
            self.model_load_time_ms = (time.perf_counter() - t0) * 1000.0
            logger.warning(
                f"DenseRetrievalManager initialization failed: {err}. "
                f"Safe fallback to lexical search is active."
            )

    def _validate_and_load_cache(self):
        """
        Validates embedding cache against corpus fingerprint and loads into memory.
        Fails clearly if missing, corrupt, or stale.
        """
        if not self.npz_path.exists():
            raise RuntimeError(
                f"Dense retrieval embedding archive missing: {self.npz_path}.\n"
                f"Automatic generation at startup is disabled. Please run:\n"
                f"  python scripts/data/generate_postal_embeddings.py"
            )
        if not self.metadata_path.exists():
            raise RuntimeError(
                f"Dense retrieval metadata missing: {self.metadata_path}.\n"
                f"Please run scripts/data/generate_postal_embeddings.py."
            )

        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        except Exception as err:
            raise RuntimeError(f"Failed to read dense retrieval metadata: {err}")

        # Corpus file validation
        workspace_root = Path(settings.DENSE_EMBEDDING_DIR).resolve().parents[2]
        corpus_file = workspace_root / "data" / "postal_documents" / "chunks" / "postal_english_chunks.jsonl"
        if not corpus_file.exists():
            raise RuntimeError(f"Postal corpus file not found: {corpus_file}")

        # Compute current corpus hash
        h = hashlib.sha256()
        with open(corpus_file, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        current_hash = h.hexdigest()

        # Staleness checks (cryptographic & structural only; not timestamp)
        if self.metadata.get("corpus_sha256") != current_hash:
            raise RuntimeError(
                f"Dense embeddings are stale! Corpus SHA256 mismatch.\n"
                f"Recorded: {self.metadata.get('corpus_sha256')}\n"
                f"Actual:   {current_hash}\n"
                f"Please re-run: python scripts/data/generate_postal_embeddings.py --force"
            )

        if self.metadata.get("chunk_count") != EXPECTED_CHUNK_COUNT:
            raise RuntimeError(
                f"Chunk count mismatch in metadata: {self.metadata.get('chunk_count')} != {EXPECTED_CHUNK_COUNT}"
            )

        if self.metadata.get("model_id") != self.model_id:
            raise RuntimeError(
                f"Model ID mismatch in metadata: {self.metadata.get('model_id')} != {self.model_id}"
            )

        # Load NPZ archive into RAM
        try:
            npz_data = np.load(self.npz_path)
            self.chunk_ids = npz_data["chunk_ids"]
            self.embeddings = npz_data["embeddings"]
        except Exception as err:
            raise RuntimeError(f"Failed to load NPZ archive {self.npz_path}: {err}")

        if len(self.chunk_ids) != EXPECTED_CHUNK_COUNT:
            raise RuntimeError(
                f"NPZ chunk count mismatch: {len(self.chunk_ids)} != {EXPECTED_CHUNK_COUNT}"
            )
        if self.embeddings.shape != (EXPECTED_CHUNK_COUNT, EXPECTED_DIM):
            raise RuntimeError(
                f"NPZ embeddings shape mismatch: {self.embeddings.shape} != ({EXPECTED_CHUNK_COUNT}, {EXPECTED_DIM})"
            )

    def _load_local_model(self):
        """
        Loads the SentenceTransformer model strictly from local files.
        Fails clearly if local weights are not present.
        """
        from sentence_transformers import SentenceTransformer
        try:
            self.model = SentenceTransformer(self.model_id, local_files_only=True)
        except Exception as err:
            raise RuntimeError(
                f"Failed to load local embedding model '{self.model_id}'.\n"
                f"Ensure model weights are cached locally. Automatic download is disabled.\n"
                f"Detail: {err}"
            )

    def encode_query(self, query: str) -> Tuple[np.ndarray, float]:
        """
        Encodes a single query string to a unit-normalized float32 vector.
        Returns: (query_vector, latency_ms)
        """
        t0 = time.perf_counter()
        q_emb = self.model.encode(
            query,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return q_emb.astype(np.float32), latency_ms

    def search(
        self,
        query: str,
        top_k: int = 20
    ) -> Tuple[List[Tuple[str, float, int]], float, float]:
        """
        Performs dense semantic search against the 228 pre-computed chunk embeddings.
        
        Returns:
            results: List of (chunk_id, cosine_similarity, dense_rank)
            encode_time_ms: Query embedding generation time in ms
            similarity_time_ms: Matrix dot product + sorting time in ms
        """
        if not self.is_available:
            raise RuntimeError(f"Dense retrieval is unavailable: {self.error_reason}")

        if not query or not query.strip():
            return [], 0.0, 0.0

        # 1. Query Encoding
        q_emb, encode_time_ms = self.encode_query(query.strip())

        # 2. Vectorized Cosine Similarity
        t0 = time.perf_counter()
        sims = np.dot(self.embeddings, q_emb)

        # 3. Deterministic Sorting: similarity descending, chunk_id ascending
        # Create structured array for completely deterministic tie-breaking
        dtype = [("chunk_id", "U50"), ("sim", "f4"), ("idx", "i4")]
        structured = np.empty(len(self.chunk_ids), dtype=dtype)
        structured["chunk_id"] = self.chunk_ids
        structured["sim"] = sims
        structured["idx"] = np.arange(len(self.chunk_ids))

        # Sort by similarity descending, then chunk_id ascending
        # Lexsort uses keys in reverse order: secondary first, primary second
        order = np.lexsort((structured["chunk_id"], -structured["sim"]))
        sorted_structured = structured[order]

        similarity_time_ms = (time.perf_counter() - t0) * 1000.0

        # Extract ranked results
        results = []
        for rank, item in enumerate(sorted_structured[:top_k], start=1):
            results.append((
                str(item["chunk_id"]),
                float(round(float(item["sim"]), 5)),
                rank
            ))

        return results, encode_time_ms, similarity_time_ms
