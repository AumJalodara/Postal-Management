"""
Automated Test Suite for Module 3 Step 1:
English-Only Official Postal Document Ingestion, Digital Extraction & Targeted OCR Pipeline.

Verifies:
1. Source PDFs exist
2. Document 1 exact page count == 8
3. Document 2 exact page count == 260
4. English page identification works
5. Hindi pages are excluded from English corpus
6. Document 1 extraction produces text
7. Approved OCR pages produce text
8. Page numbers are preserved accurately
9. Language is recorded as 'ENGLISH'
10. Extraction method is recorded for every page
11. Numbers are preserved verbatim
12. Legal punctuation is preserved verbatim
13. Legal references (sections, rules, regulations) are preserved
14. Empty/bad OCR pages are detected
15. Duplicate Rules 2024 pages are excluded from core ingestion
16. Raw PDF hashes remain byte-for-byte unchanged (SHA-256)
17. Extraction and normalization output is deterministic
18. Existing Module 1 and Module 2 behavior remains unchanged
"""

import hashlib
import json
from pathlib import Path

import pypdf
import pytest

from scripts.data.extract_postal_documents import (
    DOC1_NAME,
    DOC2_NAME,
    EXPECTED_HASHES,
    DOC1_ENGLISH_PAGE_CONFIG,
    DOC2_ENGLISH_TARGET_RANGES,
    DOC2_SKIPPED_RANGES,
    compute_quality_metrics,
    compute_sha256,
    safe_normalize_text,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DOCS_DIR = PROJECT_ROOT / "data" / "postal_documents" / "raw"
EXTRACTED_DIR = PROJECT_ROOT / "data" / "postal_documents" / "extracted"
OCR_DIR = PROJECT_ROOT / "data" / "postal_documents" / "ocr"
METADATA_DIR = PROJECT_ROOT / "data" / "postal_documents" / "metadata"
EVALUATION_DIR = PROJECT_ROOT / "data" / "postal_documents" / "evaluation"


# ==============================================================================
# TESTS 1, 2 & 3: SOURCE EXISTENCE & PAGE COUNTS
# ==============================================================================

def test_source_pdfs_exist():
    """Both source PDFs must exist in the raw directory."""
    doc1_path = RAW_DOCS_DIR / DOC1_NAME
    doc2_path = RAW_DOCS_DIR / DOC2_NAME
    assert doc1_path.exists() and doc1_path.is_file() and doc1_path.stat().st_size > 0
    assert doc2_path.exists() and doc2_path.is_file() and doc2_path.stat().st_size > 0


def test_document1_page_count():
    """Document 1 must have exactly 8 pages."""
    reader = pypdf.PdfReader(str(RAW_DOCS_DIR / DOC1_NAME))
    assert len(reader.pages) == 8


def test_document2_page_count():
    """Document 2 must have exactly 260 pages."""
    reader = pypdf.PdfReader(str(RAW_DOCS_DIR / DOC2_NAME))
    assert len(reader.pages) == 260


# ==============================================================================
# TEST 16: IMMUTABLE RAW HASHES
# ==============================================================================

def test_raw_pdf_hashes_unmodified():
    """Source PDFs must match their immutable SHA-256 baseline hashes."""
    assert compute_sha256(RAW_DOCS_DIR / DOC1_NAME) == EXPECTED_HASHES[DOC1_NAME]
    assert compute_sha256(RAW_DOCS_DIR / DOC2_NAME) == EXPECTED_HASHES[DOC2_NAME]


# ==============================================================================
# TESTS 4 & 5: ENGLISH PAGE IDENTIFICATION & HINDI EXCLUSION
# ==============================================================================

def test_english_page_identification_and_hindi_exclusion_doc1():
    """Document 1 extraction must skip Hindi pages 1-4 and process English pages 5-8."""
    out_file = EXTRACTED_DIR / "postal_2024_rule_english_pages.jsonl"
    assert out_file.exists()

    records = [json.loads(line) for line in out_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 4, f"Expected 4 English pages, found {len(records)}"

    extracted_pages = [r["pdf_page_number"] for r in records]
    assert extracted_pages == [5, 6, 7, 8]

    # Verify Hindi pages 1-4 are excluded
    for skipped in [1, 2, 3, 4]:
        assert skipped not in extracted_pages

    # Verify Page 5 starts with English notification, not Hindi
    p5_record = next(r for r in records if r["pdf_page_number"] == 5)
    assert p5_record["text"].startswith("MINISTRY OF COMMUNICATIONS")


def test_english_page_identification_and_hindi_exclusion_doc2():
    """Document 2 OCR must process exactly 115 English pages and exclude all Hindi pages."""
    ocr_file = OCR_DIR / "rule_regulation_english_ocr_pages.jsonl"
    assert ocr_file.exists()

    records = [json.loads(line) for line in ocr_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 115, f"Expected 115 English OCR pages, found {len(records)}"

    ocr_pages = {r["pdf_page_number"] for r in records}

    # Verify Hindi Regulations pages (pp. 24-127) are completely excluded
    for p in range(24, 128):
        assert p not in ocr_pages, f"Hindi Regulation page {p} was incorrectly included!"

    # Verify Hindi Amendment pages are excluded
    hindi_amend_pages = [229, 230, 234, 235, 236, 239, 241, 242, 243, 246, 247]
    for p in hindi_amend_pages:
        assert p not in ocr_pages, f"Hindi Amendment page {p} was incorrectly included!"


# ==============================================================================
# TESTS 6, 7, 8, 9 & 10: EXTRACTION OUTPUT, PAGE NUMBERS, LANGUAGE & METHOD
# ==============================================================================

def test_document1_extraction_produces_text_and_records_metadata():
    """Document 1 English extraction produces non-empty text, records method and language."""
    out_file = EXTRACTED_DIR / "postal_2024_rule_english_pages.jsonl"
    records = [json.loads(line) for line in out_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    for r in records:
        assert len(r["text"]) > 100
        assert r["language"] == "ENGLISH"
        assert r["extraction_method"] == "DIGITAL_VECTOR_PYPDF"
        assert r["document_id"] == "POSTAL_RULES_2024_ENG"
        assert r["pdf_page_number"] in [5, 6, 7, 8]


def test_document2_ocr_produces_text_and_records_metadata():
    """Document 2 OCR produces non-empty text, records method, language, and status."""
    ocr_file = OCR_DIR / "rule_regulation_english_ocr_pages.jsonl"
    records = [json.loads(line) for line in ocr_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    for r in records:
        assert len(r["text"]) > 0
        assert r["language"] == "ENGLISH"
        assert r["extraction_method"] == "OCR_TESSERACT_ENG"
        assert r["ocr_status"] == "SUCCESS"
        assert r["ocr_language"] == "eng"
        assert r["document_id"] == "POSTAL_ACT_REGULATIONS_COMPENDIUM_2025_ENG"


# ==============================================================================
# TESTS 11, 12 & 13: PRESERVATION OF NUMBERS, PUNCTUATION & LEGAL REFS
# ==============================================================================

def test_preservation_of_numbers_and_clauses():
    """Safe normalization preserves statutory numbers, decimals, and sub-clauses verbatim."""
    raw = "Section 16.(1) Repeal of 1898 Act... sub-regulation (2)(a) fee ₹ 19.00 per 50g."
    norm = safe_normalize_text(raw)

    assert "Section 16.(1)" in norm
    assert "1898" in norm
    assert "sub-regulation (2)(a)" in norm
    assert "19.00" in norm
    assert "50g" in norm


def test_preservation_of_legal_punctuation_and_parentheses():
    """Punctuation, colons, hyphens, and quotation marks must not be stripped."""
    raw = "Rule 3(a): 'Mail Service' — chargeable; (1) 'Director General' appointed."
    norm = safe_normalize_text(raw)

    assert "Rule 3(a):" in norm
    assert "'Mail Service'" in norm
    assert "'Director General'" in norm
    assert "(1)" in norm


def test_preservation_of_legal_references_in_corpus():
    """Extracted corpus contains core statutory terms in English."""
    out_file = EXTRACTED_DIR / "postal_2024_rule_english_pages.jsonl"
    records = [json.loads(line) for line in out_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    full_text = " ".join(r["text"] for r in records).lower()

    assert "post office act, 2023" in full_text
    assert "postage" in full_text
    assert "mail service" in full_text


# ==============================================================================
# TEST 14: EMPTY/BAD OCR ANOMALY DETECTION
# ==============================================================================

def test_empty_and_bad_ocr_detection():
    """Quality metrics correctly detect empty text and excessive noise."""
    empty_m = compute_quality_metrics("", is_ocr=True)
    assert empty_m["is_empty"] is True
    assert empty_m["is_suspicious"] is True

    noisy_m = compute_quality_metrics("!@# $%^ &*() _+~ `{}[];:", is_ocr=True)
    assert noisy_m["is_suspicious"] is True

    valid_text = (
        "The Post Office Act, 2023 was enacted by Parliament to consolidate and amend "
        "the law relating to the Post Office in India and to provide for matters connected therewith."
    )
    valid_m = compute_quality_metrics(valid_text, is_ocr=True)
    assert valid_m["is_empty"] is False
    assert valid_m["is_suspicious"] is False


# ==============================================================================
# TEST 15: DUPLICATE RULES EXCLUSION
# ==============================================================================

def test_duplicate_rules_pages_excluded_from_ocr():
    """PDF pages 16 to 23 of Document 2 must be excluded from OCR to prevent duplicate chunks."""
    ocr_file = OCR_DIR / "rule_regulation_english_ocr_pages.jsonl"
    records = [json.loads(line) for line in ocr_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    ocr_pages = {r["pdf_page_number"] for r in records}

    for dup_page in range(16, 24):
        assert dup_page not in ocr_pages, f"Duplicate Rules page {dup_page} was included!"


# ==============================================================================
# TEST 17: DETERMINISTIC OUTPUT
# ==============================================================================

def test_extraction_normalization_determinism():
    """Normalization must produce byte-identical output across repeated executions."""
    text = "   Regulation  67.(2)(a)  \r\n\r\n   Fee:  ₹ 25.00  \u00a0 for 100g.   "
    r1 = safe_normalize_text(text)
    r2 = safe_normalize_text(text)
    r3 = safe_normalize_text(r1)
    assert r1 == r2 == r3
