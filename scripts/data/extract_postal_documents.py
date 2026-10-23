"""
English-Only Document Ingestion & Text Extraction Layer for Official Postal Documents.
AI-Powered Intelligent Government Postal Management and Information Retrieval System.
Module 3 — Step 1 (Scope: English-Only Corpus).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pypdf
import pytesseract


# ==============================================================================
# CONFIGURATION & ENVIRONMENT SETUP
# ==============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DOCS_DIR = PROJECT_ROOT / "data" / "postal_documents" / "raw"
EXTRACTED_DIR = PROJECT_ROOT / "data" / "postal_documents" / "extracted"
OCR_DIR = PROJECT_ROOT / "data" / "postal_documents" / "ocr"
METADATA_DIR = PROJECT_ROOT / "data" / "postal_documents" / "metadata"
EVALUATION_DIR = PROJECT_ROOT / "data" / "postal_documents" / "evaluation"

DOC1_NAME = "postal 2024 rule.pdf"
DOC2_NAME = "rule and regulation.pdf"

# Verified SHA-256 hashes of original raw documents (immutable baseline)
EXPECTED_HASHES = {
    DOC1_NAME: "325fd309ffa37190dffceae745e01aeda9fb9add6c57dba8c6409f9a7f2d95f9",
    DOC2_NAME: "ca7be6edc8cbe0b8145cc69e6d7bc9e329c2cf4acd1f746a541f1c726257d45e",
}

# ==============================================================================
# DOCUMENT 1 ENGLISH CONFIGURATION (postal 2024 rule.pdf - 8 pages total)
# ==============================================================================
# Pages 1-4: Hindi Gazette publication (SKIPPED for English corpus)
# Page 5: Mixed (Top half is Hindi; bottom half starts English Notification at "MINISTRY OF COMMUNICATIONS")
# Pages 6-8: 100% English statutory rules
DOC1_ENGLISH_PAGE_CONFIG = {
    "skipped_pages": [1, 2, 3, 4],
    "mixed_pages": [5],
    "pure_english_pages": [6, 7, 8],
    "english_start_marker_p5": "MINISTRY OF COMMUNICATIONS",
}

# ==============================================================================
# DOCUMENT 2 ENGLISH TARGET & SKIPPED RANGES (rule and regulation.pdf - 260 pp)
# ==============================================================================
# Offset note: 11 front-matter pages precede Document Page 1 (Act begins at PDF Page 12)
DOC2_ENGLISH_TARGET_RANGES = [
    # (start_pdf_page, end_pdf_page, section_title, doc_type, pub_date)
    (12, 15, "The Post Office Act, 2023", "STATUTORY_ACT", "2023-12-24"),
    (128, 228, "The Post Office Regulations, 2024", "STATUTORY_REGULATIONS", "2024-12-16"),
    (231, 233, "Post Office (Amendment) Regulations, 2025 (1st Amendment)", "AMENDMENT_REGULATIONS", "2025-01-01"),
    (237, 238, "Post Office (Second Amendment) Regulations, 2025 (Gyan Post)", "AMENDMENT_REGULATIONS", "2025-01-01"),
    (240, 240, "Post Office (Third Amendment) Regulations, 2025 (Tariffs)", "AMENDMENT_REGULATIONS", "2025-01-01"),
    (244, 245, "Post Office (Fourth Amendment) Regulations, 2025 (Speed Post Document)", "AMENDMENT_REGULATIONS", "2025-01-01"),
    (248, 249, "Post Office (Fifth Amendment) Regulations, 2025", "AMENDMENT_REGULATIONS", "2025-01-01"),
]

# Total targeted English pages: 4 + 101 + 3 + 2 + 1 + 2 + 2 = 115 pages

DOC2_SKIPPED_RANGES = [
    {"pages": "1-10", "count": 10, "classification": "NON_CONTENT", "reason": "Cover, portraits, forewords, institutional messages"},
    {"pages": "11", "count": 1, "classification": "NON_CONTENT", "reason": "Compendium Master Index / Table of Contents"},
    {"pages": "16-23", "count": 8, "classification": "DUPLICATE", "reason": "Duplicate of Rules 2024 (ingested from clean vector Document 1)"},
    {"pages": "24-127", "count": 104, "classification": "HINDI", "reason": "The Post Office Regulations, 2024 Hindi translation (Regulations 1 to 115)"},
    {"pages": "229-230", "count": 2, "classification": "HINDI", "reason": "1st Amendment Regulations, 2025 Hindi Gazette notification"},
    {"pages": "234-236", "count": 3, "classification": "HINDI", "reason": "2nd Amendment Regulations, 2025 Hindi Gazette notification"},
    {"pages": "239", "count": 1, "classification": "HINDI", "reason": "3rd Amendment Regulations, 2025 Hindi Gazette notification"},
    {"pages": "241-243", "count": 3, "classification": "HINDI", "reason": "4th Amendment Regulations, 2025 Hindi Gazette notification"},
    {"pages": "246-247", "count": 2, "classification": "HINDI", "reason": "5th Amendment Regulations, 2025 Hindi Gazette notification"},
    {"pages": "250-259", "count": 10, "classification": "NON_REGULATORY_REFERENCE", "reason": "1898 vs 2023 Comparative Matrix (historical concordance table)"},
    {"pages": "260", "count": 1, "classification": "NON_CONTENT", "reason": "Back cover"},
]
# Total skipped pages: 10 + 1 + 8 + 104 + 2 + 3 + 1 + 3 + 2 + 10 + 1 = 145 pages (115 + 145 = 260)


def configure_tesseract() -> str:
    """Configures and validates local Tesseract binary and tessdata prefix."""
    local_app_data = os.environ.get("LOCALAPPDATA", r"C:\Users\Aum\AppData\Local")
    user_tess_dir = Path(local_app_data) / "Programs" / "Tesseract-OCR"
    user_tess_exe = user_tess_dir / "tesseract.exe"

    if user_tess_exe.exists():
        pytesseract.pytesseract.tesseract_cmd = str(user_tess_exe)
        os.environ["TESSDATA_PREFIX"] = str(user_tess_dir / "tessdata")
        return str(user_tess_exe)

    return "tesseract"


# ==============================================================================
# HASHING & INTEGRITY VERIFICATION
# ==============================================================================

def compute_sha256(filepath: Path) -> str:
    """Computes SHA-256 hash of a file deterministically."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_source_integrity() -> Dict[str, Any]:
    """Verifies that both raw source PDFs exist, are uncorrupted, and unaltered."""
    results = {}
    for filename, expected_hash in EXPECTED_HASHES.items():
        filepath = RAW_DOCS_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Source file missing: {filepath}")
        actual_hash = compute_sha256(filepath)
        size_bytes = filepath.stat().st_size
        if actual_hash != expected_hash:
            raise ValueError(
                f"Source integrity check FAILED for {filename}!\n"
                f"Expected: {expected_hash}\nActual:   {actual_hash}"
            )
        results[filename] = {
            "path": str(filepath),
            "size_bytes": size_bytes,
            "sha256": actual_hash,
            "status": "VERIFIED_UNCHANGED",
        }
    return results


# ==============================================================================
# SAFE NORMALIZATION & QUALITY CHECKING
# ==============================================================================

def safe_normalize_text(text: str) -> str:
    """
    Applies only safe normalization to English statutory text.
    
    ALLOWED:
    - Unicode NFKC normalization
    - Carriage return unification (\r\n -> \n)
    - Zero-width character stripping
    - Collapse accidental repeated whitespace on the same line
    - Strip trailing space on lines
    
    PRESERVED VERBATIM:
    - All digits and numeric clauses
    - All punctuation (periods, commas, colons, semicolons, hyphens, brackets, quotes)
    - Section identifiers (e.g. '16.(1)', 'Sec. 3(i)', 'Regulation 67(2)(a)')
    - Statutory terms, negations ('not', 'shall', 'may'), currency symbols ('₹', 'Rs.')
    """
    if not text:
        return ""

    # 1. Unicode NFKC normalization (standardizes ligatures, full-width chars)
    normalized = unicodedata.normalize("NFKC", text)

    # 2. Unify line endings
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Strip zero-width / invisible control characters
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff"):
        normalized = normalized.replace(ch, "")

    # 4. Safe whitespace normalization (line by line to preserve legal paragraphs)
    cleaned_lines = []
    for line in normalized.split("\n"):
        line = line.replace("\u00a0", " ")
        parts = line.split()
        cleaned_line = " ".join(parts)
        cleaned_lines.append(cleaned_line)

    # 5. Rejoin and collapse excessive consecutive blank lines (max 2 consecutive newlines)
    result = "\n".join(cleaned_lines)
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")

    return result.strip()


def compute_quality_metrics(text: str, is_ocr: bool = False) -> Dict[str, Any]:
    """
    Computes quality and anomaly detection metrics for English extracted text.
    Flags suspicious extraction without altering original text.
    """
    char_count = len(text)
    word_count = len(text.split())
    line_count = len(text.splitlines()) if text else 0

    if char_count == 0:
        return {
            "char_count": 0,
            "word_count": 0,
            "line_count": 0,
            "alpha_ratio": 0.0,
            "digit_count": 0,
            "is_empty": True,
            "is_suspicious": True,
            "warning": "EMPTY_TEXT: No characters extracted.",
        }

    alpha_count = sum(1 for c in text if c.isalpha())
    digit_count = sum(1 for c in text if c.isdigit())
    punct_count = sum(1 for c in text if not c.isalnum() and not c.isspace())

    alpha_ratio = round(alpha_count / char_count, 4)
    suspicious_symbol_ratio = round(punct_count / char_count, 4)

    warnings = []
    is_suspicious = False

    # Check for unusually low alphabetic content (indicates OCR noise or non-English contamination)
    if char_count > 50 and alpha_ratio < 0.40:
        is_suspicious = True
        warnings.append(f"LOW_ALPHA_RATIO: {alpha_ratio:.2f} < 0.40")

    # Check for abnormally short page on dense statutory documents
    if char_count < 80:
        is_suspicious = True
        warnings.append(f"LOW_CHAR_COUNT: Only {char_count} characters extracted on page.")

    # High symbol noise ratio
    if suspicious_symbol_ratio > 0.35 and char_count > 50:
        is_suspicious = True
        warnings.append(f"HIGH_SYMBOL_RATIO: {suspicious_symbol_ratio:.2f} punctuation/symbols.")

    return {
        "char_count": char_count,
        "word_count": word_count,
        "line_count": line_count,
        "alpha_ratio": alpha_ratio,
        "digit_count": digit_count,
        "punct_count": punct_count,
        "is_empty": False,
        "is_suspicious": is_suspicious,
        "warning": "; ".join(warnings) if warnings else None,
    }


# ==============================================================================
# DOCUMENT 1: DIGITAL ENGLISH EXTRACTION (PYPDF)
# ==============================================================================

def extract_document1_english(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extracts ONLY the English statutory portion of Document 1 (postal 2024 rule.pdf).
    Skips Hindi pages (pp. 1-4).
    Filters mixed page 5 to retain only the English notification from 'MINISTRY OF COMMUNICATIONS' onwards.
    Extracts pure English pages 6-8.
    """
    reader = pypdf.PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    if total_pages != 8:
        raise ValueError(f"Document 1 expected 8 pages, found {total_pages}")

    page_records = []

    # Process English pages: 5, 6, 7, 8
    for page_num in [5, 6, 7, 8]:
        page_idx = page_num - 1
        page = reader.pages[page_idx]
        raw_text = page.extract_text() or ""

        if page_num == 5:
            # Page 5 is mixed: top half is Hindi, bottom half is English notification
            marker = DOC1_ENGLISH_PAGE_CONFIG["english_start_marker_p5"]
            marker_idx = raw_text.find(marker)
            if marker_idx != -1:
                english_text = raw_text[marker_idx:]
            else:
                english_text = raw_text
        else:
            english_text = raw_text

        normalized_text = safe_normalize_text(english_text)
        metrics = compute_quality_metrics(normalized_text, is_ocr=False)

        record = {
            "document_id": "POSTAL_RULES_2024_ENG",
            "source_filename": DOC1_NAME,
            "document_title": "The Post Office Rules, 2024",
            "document_type": "STATUTORY_RULES",
            "issuing_authority": "Ministry of Communications, Department of Posts",
            "publication_date": "2024-12-16",
            "pdf_page_number": page_num,
            "section": "Rules 1 to 10 & Schedule" if page_num >= 6 else "Preliminary & Rules 1-2(f)",
            "language": "ENGLISH",
            "extraction_method": "DIGITAL_VECTOR_PYPDF",
            "processing_version": "1.0.0",
            "quality_metrics": metrics,
            "text": normalized_text,
        }
        page_records.append(record)

    return page_records


# ==============================================================================
# DOCUMENT 2: TARGETED ENGLISH TESSERACT OCR
# ==============================================================================

def extract_document2_english_ocr(
    pdf_path: Path,
    target_ranges: List[Tuple[int, int, str, str, str]] = DOC2_ENGLISH_TARGET_RANGES,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Performs targeted local Tesseract OCR strictly on the approved English regulatory pages of Document 2.
    Skips all Hindi translation pages, portraits, indexes, duplicate rules, and historical tables.
    """
    reader = pypdf.PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    if total_pages != 260:
        raise ValueError(f"Document 2 expected 260 pages, found {total_pages}")

    tesseract_version = pytesseract.get_tesseract_version().public
    page_records = []
    stats = {
        "total_pdf_pages": total_pages,
        "pages_processed": 0,
        "successful_pages": 0,
        "suspicious_pages": 0,
        "failed_pages": 0,
        "total_chars_extracted": 0,
        "total_words_extracted": 0,
        "total_ocr_time_seconds": 0.0,
    }

    start_total_time = time.time()

    for start_page, end_page, title, doc_type, pub_date in target_ranges:
        print(f"  Processing English section '{title}' (PDF pages {start_page} to {end_page})...")
        for page_num in range(start_page, end_page + 1):
            page_idx = page_num - 1
            page = reader.pages[page_idx]

            ocr_start = time.time()
            extracted_text = ""
            ocr_status = "SUCCESS"
            error_msg = None

            try:
                images = page.images
                if len(images) == 0:
                    ocr_status = "NO_IMAGE_FOUND"
                    error_msg = "No image XObjects found on scanned page."
                else:
                    pil_img = images[0].image
                    # Execute local Tesseract OCR using English language model
                    raw_ocr = pytesseract.image_to_string(pil_img, lang="eng")
                    extracted_text = safe_normalize_text(raw_ocr)
            except Exception as exc:
                ocr_status = "OCR_ERROR"
                error_msg = f"{type(exc).__name__}: {str(exc)}"

            ocr_elapsed = round(time.time() - ocr_start, 3)
            metrics = compute_quality_metrics(extracted_text, is_ocr=True)

            if error_msg:
                metrics["warning"] = error_msg
                metrics["is_suspicious"] = True

            record = {
                "document_id": "POSTAL_ACT_REGULATIONS_COMPENDIUM_2025_ENG",
                "source_filename": DOC2_NAME,
                "document_title": title,
                "document_type": doc_type,
                "issuing_authority": "Department of Posts, Ministry of Communications, Government of India",
                "publication_date": pub_date,
                "pdf_page_number": page_num,
                "section": title,
                "language": "ENGLISH",
                "extraction_method": "OCR_TESSERACT_ENG",
                "ocr_engine_version": str(tesseract_version),
                "ocr_language": "eng",
                "ocr_status": ocr_status,
                "ocr_elapsed_seconds": ocr_elapsed,
                "processing_version": "1.0.0",
                "quality_metrics": metrics,
                "text": extracted_text,
            }
            page_records.append(record)

            stats["pages_processed"] += 1
            if ocr_status == "SUCCESS":
                stats["successful_pages"] += 1
            else:
                stats["failed_pages"] += 1

            if metrics["is_suspicious"]:
                stats["suspicious_pages"] += 1

            stats["total_chars_extracted"] += metrics["char_count"]
            stats["total_words_extracted"] += metrics["word_count"]

    stats["total_ocr_time_seconds"] = round(time.time() - start_total_time, 2)
    return page_records, stats


# ==============================================================================
# PIPELINE EXECUTION & DETERMINISTIC STORAGE
# ==============================================================================

def run_english_extraction_pipeline(
    verify_only: bool = False,
) -> Dict[str, Any]:
    """Runs the English-only document extraction and OCR pipeline deterministically."""
    print("=" * 75)
    print("MODULE 3 STEP 1: ENGLISH-ONLY POSTAL DOCUMENT EXTRACTION & OCR PIPELINE")
    print("=" * 75)

    # 1. Environment & Tesseract Configuration
    tess_cmd = configure_tesseract()
    tess_version = pytesseract.get_tesseract_version().public
    print(f"1. Tesseract OCR Engine: {tess_cmd} (v{tess_version})")
    print(f"   pypdf Version:        {pypdf.__version__}")
    print(f"   pytesseract Version:  {pytesseract.__version__}")
    print(f"   Language Scope:       ENGLISH ONLY (Hindi excluded)")

    # 2. Source Integrity Verification
    print("\n2. Verifying Source Documents...")
    integrity = verify_source_integrity()
    for name, info in integrity.items():
        print(f"   [OK] {name}: {info['size_bytes']:,} bytes | SHA256: {info['sha256'][:16]}...")

    if verify_only:
        return {"status": "INTEGRITY_VERIFIED_ONLY", "integrity": integrity}

    # Ensure output directories exist
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Process Document 1 (English Digital Extraction)
    print(f"\n3. Extracting Document 1: {DOC1_NAME} (English Digital Vector via pypdf)...")
    doc1_records = extract_document1_english(RAW_DOCS_DIR / DOC1_NAME)
    print(f"   Extracted {len(doc1_records)} English pages (PDF pp. 5-8). Skipped Hindi pp. 1-4.")
    doc1_chars = sum(r["quality_metrics"]["char_count"] for r in doc1_records)
    print(f"   Total English Characters in Doc 1: {doc1_chars:,}")

    doc1_out_file = EXTRACTED_DIR / "postal_2024_rule_english_pages.jsonl"
    with open(doc1_out_file, "w", encoding="utf-8") as f:
        for r in doc1_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"   Saved to: {doc1_out_file.relative_to(PROJECT_ROOT)}")

    # 4. Process Document 2 (Targeted English Tesseract OCR)
    print(f"\n4. Processing Document 2: {DOC2_NAME} (Targeted English OCR)...")
    doc2_records, doc2_stats = extract_document2_english_ocr(RAW_DOCS_DIR / DOC2_NAME)
    print(f"   OCR Completed: {doc2_stats['pages_processed']} English pages in {doc2_stats['total_ocr_time_seconds']}s.")
    print(f"   Successful: {doc2_stats['successful_pages']} | Suspicious: {doc2_stats['suspicious_pages']} | Failed: {doc2_stats['failed_pages']}")
    print(f"   Total Characters Extracted via English OCR: {doc2_stats['total_chars_extracted']:,}")

    doc2_out_file = OCR_DIR / "rule_regulation_english_ocr_pages.jsonl"
    with open(doc2_out_file, "w", encoding="utf-8") as f:
        for r in doc2_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"   Saved to: {doc2_out_file.relative_to(PROJECT_ROOT)}")

    # 5. Save Provenance & Evaluation Metadata
    print("\n5. Generating Provenance & Evaluation Metadata...")
    provenance = {
        "pipeline_step": "MODULE_3_STEP_1_ENGLISH_EXTRACTION",
        "scope": "ENGLISH_ONLY",
        "timestamp_generated": "2026-09-11T01:40:00Z",
        "software_environment": {
            "python_version": sys.version,
            "pypdf_version": pypdf.__version__,
            "pytesseract_version": pytesseract.__version__,
            "tesseract_version": str(tess_version),
            "ocr_language": "eng",
        },
        "source_documents": integrity,
        "document_1_english_selection": {
            "source_filename": DOC1_NAME,
            "total_pages": 8,
            "english_pages": [5, 6, 7, 8],
            "skipped_hindi_pages": [1, 2, 3, 4],
            "mixed_page_treatment": "Page 5 filtered from 'MINISTRY OF COMMUNICATIONS' to retain English notification only",
        },
        "document_2_english_selection": {
            "source_filename": DOC2_NAME,
            "total_pages": 260,
            "english_ocr_pages_count": len(doc2_records),
            "target_page_ranges": [
                {"start": r[0], "end": r[1], "title": r[2], "type": r[3], "pub_date": r[4]}
                for r in DOC2_ENGLISH_TARGET_RANGES
            ],
            "skipped_page_ranges": DOC2_SKIPPED_RANGES,
            "skipped_pages_count": sum(s["count"] for s in DOC2_SKIPPED_RANGES),
        },
        "duplicate_rules_policy": {
            "authoritative_source": DOC1_NAME,
            "authoritative_pages": "Pages 5-8 (English Gazette)",
            "duplicate_source": DOC2_NAME,
            "duplicate_pages": "PDF Pages 16-23 (Compendium Document Pages 5-12)",
            "action_taken": "EXCLUDED_FROM_DOC2_OCR_TO_PREVENT_DUPLICATE_CHUNKS",
        },
    }

    provenance_file = METADATA_DIR / "document_provenance.json"
    with open(provenance_file, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2, ensure_ascii=False)
    print(f"   Saved Provenance: {provenance_file.relative_to(PROJECT_ROOT)}")

    evaluation = {
        "pipeline_step": "MODULE_3_STEP_1_ENGLISH_EVALUATION",
        "document_1_english_summary": {
            "filename": DOC1_NAME,
            "extracted_pages": len(doc1_records),
            "total_characters": doc1_chars,
            "pdf_pages": [r["pdf_page_number"] for r in doc1_records],
        },
        "document_2_english_ocr_summary": doc2_stats,
        "suspicious_pages_review": [
            {
                "pdf_page": r["pdf_page_number"],
                "section": r["document_title"],
                "warning": r["quality_metrics"]["warning"],
                "char_count": r["quality_metrics"]["char_count"],
                "alpha_ratio": r["quality_metrics"]["alpha_ratio"],
            }
            for r in doc2_records
            if r["quality_metrics"]["is_suspicious"]
        ],
    }

    eval_file = EVALUATION_DIR / "extraction_quality_summary.json"
    with open(eval_file, "w", encoding="utf-8") as f:
        json.dump(evaluation, f, indent=2, ensure_ascii=False)
    print(f"   Saved Evaluation: {eval_file.relative_to(PROJECT_ROOT)}")

    print("\n" + "=" * 75)
    print("MODULE 3 STEP 1: ENGLISH-ONLY EXTRACTION & OCR PIPELINE COMPLETED")
    print("=" * 75)

    return {
        "doc1_english_pages": len(doc1_records),
        "doc2_english_ocr_pages": len(doc2_records),
        "doc2_stats": doc2_stats,
        "doc1_out_file": str(doc1_out_file),
        "doc2_out_file": str(doc2_out_file),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract English postal documents via pypdf and Tesseract OCR")
    parser.add_argument("--verify-only", action="store_true", help="Only verify source PDF hashes and exit")
    args = parser.parse_args()

    run_english_extraction_pipeline(verify_only=args.verify_only)
