"""
Deterministic Offline Embedding Generator for Postal Document Chunks.

Encodes the 228 verified postal legal chunks using sentence-transformers/all-MiniLM-L6-v2
under strictly local, CPU-only execution (local_files_only=True).

Generates:
1. data/postal_documents/embeddings/postal_chunk_embeddings.npz
   - chunk_ids: ndarray of str (shape 228,)
   - embeddings: ndarray of float32 unit-normalized vectors (shape 228, 384)
2. data/postal_documents/embeddings/metadata.json
   - Cryptographic corpus SHA256 hash
   - Chunk count (exactly 228)
   - Model identifier and embedding dimension
   - Effective sequence length and preprocessing template
   - Staleness validation metadata
"""

import os
import sys
import json
import time
import hashlib
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_FILE = WORKSPACE_ROOT / "data" / "postal_documents" / "chunks" / "postal_english_chunks.jsonl"
EMBEDDINGS_DIR = WORKSPACE_ROOT / "data" / "postal_documents" / "embeddings"
NPZ_FILE = EMBEDDINGS_DIR / "postal_chunk_embeddings.npz"
METADATA_FILE = EMBEDDINGS_DIR / "metadata.json"

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
PREPROCESSING_VERSION = "1.0.0"
CHUNK_TEXT_TEMPLATE = "{heading}. {legal_reference}.\n{text}"
EXPECTED_CHUNK_COUNT = 228
EXPECTED_DIM = 384


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_chunks(filepath: Path) -> List[Dict[str, Any]]:
    """Loads and validates chunks from JSONL file."""
    if not filepath.exists():
        raise FileNotFoundError(f"Corpus chunks file not found: {filepath}")

    chunks = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line.strip()))

    if len(chunks) != EXPECTED_CHUNK_COUNT:
        raise ValueError(f"Expected exactly {EXPECTED_CHUNK_COUNT} chunks, found {len(chunks)}")

    # Sort deterministically by chunk_id
    chunks.sort(key=lambda c: c["chunk_id"])
    return chunks


def format_chunk_text(chunk: Dict[str, Any]) -> str:
    """Applies standardized deterministic text template for embedding."""
    heading = (chunk.get("heading") or "").strip()
    ref = (chunk.get("legal_reference") or "").strip()
    body = (chunk.get("text") or "").strip()
    return f"{heading}. {ref}.\n{body}"


def verify_embedding_cache() -> Tuple[bool, str]:
    """
    Validates cache integrity using cryptographic and structural fingerprints.
    Does NOT use timestamps for staleness.
    """
    if not NPZ_FILE.exists():
        return False, f"Embedding archive missing: {NPZ_FILE}"
    if not METADATA_FILE.exists():
        return False, f"Metadata file missing: {METADATA_FILE}"

    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as e:
        return False, f"Failed to parse metadata.json: {e}"

    # 1. Corpus SHA256 validation
    current_corpus_hash = compute_sha256(CHUNKS_FILE)
    if meta.get("corpus_sha256") != current_corpus_hash:
        return False, f"Corpus SHA256 mismatch (recorded: {meta.get('corpus_sha256')}, actual: {current_corpus_hash})"

    # 2. Model ID validation
    if meta.get("model_id") != MODEL_ID:
        return False, f"Model ID mismatch (recorded: {meta.get('model_id')}, expected: {MODEL_ID})"

    # 3. Preprocessing version validation
    if meta.get("preprocessing_version") != PREPROCESSING_VERSION:
        return False, f"Preprocessing version mismatch (recorded: {meta.get('preprocessing_version')}, expected: {PREPROCESSING_VERSION})"

    # 4. Chunk count validation
    if meta.get("chunk_count") != EXPECTED_CHUNK_COUNT:
        return False, f"Chunk count mismatch in metadata (recorded: {meta.get('chunk_count')}, expected: {EXPECTED_CHUNK_COUNT})"

    # 5. NPZ content validation
    try:
        data = np.load(NPZ_FILE)
        chunk_ids = data["chunk_ids"]
        embeddings = data["embeddings"]
    except Exception as e:
        return False, f"Failed to load NPZ archive: {e}"

    if len(chunk_ids) != EXPECTED_CHUNK_COUNT:
        return False, f"NPZ chunk_ids count mismatch: {len(chunk_ids)} != {EXPECTED_CHUNK_COUNT}"
    if embeddings.shape != (EXPECTED_CHUNK_COUNT, EXPECTED_DIM):
        return False, f"NPZ embeddings shape mismatch: {embeddings.shape} != ({EXPECTED_CHUNK_COUNT}, {EXPECTED_DIM})"

    return True, "Cache is valid and fully synchronized with corpus."


def generate_embeddings(force: bool = False) -> Dict[str, Any]:
    """Generates and writes embeddings cache."""
    print("=" * 70)
    print(" POSTAL DOCUMENT CHUNK EMBEDDING GENERATION")
    print("=" * 70)
    print(f"Corpus File    : {CHUNKS_FILE}")
    print(f"Target Output  : {EMBEDDINGS_DIR}")
    print(f"Model ID       : {MODEL_ID}")

    is_valid, msg = verify_embedding_cache()
    if is_valid and not force:
        print(f"\n[CACHE HIT] {msg}")
        print("Skipping generation. Use --force to regenerate.")
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    if not is_valid:
        print(f"\n[CACHE INVALID / MISSING]: {msg}")

    print("\nLoading corpus chunks...")
    chunks = load_chunks(CHUNKS_FILE)
    corpus_sha256 = compute_sha256(CHUNKS_FILE)
    chunk_ids = [c["chunk_id"] for c in chunks]
    formatted_texts = [format_chunk_text(c) for c in chunks]
    print(f"Loaded {len(chunks)} chunks (Corpus SHA256: {corpus_sha256[:16]}...)")

    print(f"\nLoading SentenceTransformer model '{MODEL_ID}' (local_files_only=True)...")
    from sentence_transformers import SentenceTransformer
    try:
        t0 = time.perf_counter()
        model = SentenceTransformer(MODEL_ID, local_files_only=True)
        model_load_time = time.perf_counter() - t0
        print(f"Model loaded in {model_load_time:.2f}s.")
    except Exception as e:
        raise RuntimeError(
            f"Failed to load local model '{MODEL_ID}'. Ensure the model has been downloaded "
            f"locally and network requests are disabled. Detail: {e}"
        )

    max_seq_len = int(model.max_seq_length)
    tok_max_len = int(model.tokenizer.model_max_length)
    dim = int(model.get_sentence_embedding_dimension() if hasattr(model, "get_sentence_embedding_dimension") else model.get_embedding_dimension())
    print(f"  Max sequence length : {max_seq_len}")
    print(f"  Tokenizer max length: {tok_max_len}")
    print(f"  Embedding dimension : {dim}")
    assert dim == EXPECTED_DIM, f"Expected dim {EXPECTED_DIM}, got {dim}"

    print(f"\nEncoding {len(formatted_texts)} chunks on CPU with L2 normalization...")
    t0 = time.perf_counter()
    embeddings = model.encode(
        formatted_texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32
    )
    encode_time = time.perf_counter() - t0
    print(f"Encoding completed in {encode_time:.2f}s ({encode_time / len(chunks) * 1000:.1f} ms/chunk).")
    print(f"Embeddings array shape: {embeddings.shape}, dtype: {embeddings.dtype}")

    # Ensure output directory exists
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    # Save NPZ archive
    print(f"\nSaving NPZ archive to: {NPZ_FILE}...")
    np.savez_compressed(
        NPZ_FILE,
        chunk_ids=np.array(chunk_ids, dtype=str),
        embeddings=embeddings.astype(np.float32)
    )
    npz_size = NPZ_FILE.stat().st_size
    print(f"NPZ archive written ({npz_size:,} bytes, {npz_size / 1024:.1f} KB).")

    # Save metadata
    metadata = {
        "corpus_file": CHUNKS_FILE.name,
        "corpus_sha256": corpus_sha256,
        "chunk_count": len(chunks),
        "model_id": MODEL_ID,
        "embedding_dim": dim,
        "max_seq_length": max_seq_len,
        "tokenizer_max_length": tok_max_len,
        "preprocessing_version": PREPROCESSING_VERSION,
        "chunk_text_template": CHUNK_TEXT_TEMPLATE,
        "encoding_time_seconds": round(encode_time, 2),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    print(f"Saving metadata to: {METADATA_FILE}...")
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("\nVerification check of written cache...")
    valid, check_msg = verify_embedding_cache()
    if not valid:
        raise RuntimeError(f"Cache verification failed immediately after generation: {check_msg}")
    print(f"[VERIFIED] {check_msg}")
    print("=" * 70 + "\n")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate offline postal chunk embeddings.")
    parser.add_argument("--force", action="store_true", help="Force regeneration even if cache is valid.")
    parser.add_argument("--verify", action="store_true", help="Only verify existing cache without generating.")
    args = parser.parse_args()

    if args.verify:
        valid, msg = verify_embedding_cache()
        print(f"Cache Verification: {'PASSED' if valid else 'FAILED'} - {msg}")
        sys.exit(0 if valid else 1)
    else:
        generate_embeddings(force=args.force)
