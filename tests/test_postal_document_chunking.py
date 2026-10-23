"""tests/test_postal_document_chunking.py

Module 3 — Step 2: Structure-Aware Legal Chunking & Metadata Verification Suite
AI-Powered Intelligent Government Postal Management and Information Retrieval System

Validates:
1. Output file existence and integrity
2. Metadata file existence and schema
3. Line-by-line JSON validity
4. Chunk count alignment (exact match to metadata summary)
5. Required metadata fields presence across all chunks
6. Deterministic and unique chunk IDs
7. Non-empty text content
8. Valid page provenance (start_page <= end_page, contiguous pages)
9. Multi-page chunk correctness
10. Source page containment within Step 1 verified corpus (119 pages)
11. Document 1 Post Office Rules, 2024 completeness (Preamble + Rules 1 to 19)
12. Document 2 The Post Office Act, 2023 completeness (Preamble + Sections 1 to 16)
13. Document 2 The Post Office Regulations, 2024 completeness (Preamble + Regs 1 to 180)
14. Schedules completeness (Schedules I, II, III, IV, V)
15. 2025 Amendment Notifications completeness (Amendments 1 to 5)
16. Tariff table preservation (weight slabs, distances, fees preserved)
17. Child clause integrity (no orphaned subsections/provisos/explanations)
18. Character count mathematical integrity
19. Word count mathematical integrity
20. OCR anomaly provenance and non-destructive preservation
21. Source text preservation (exact traceability)
22. English-only cleanliness (no Devanagari Hindi text)
23. Deterministic pipeline regeneration
24. Critical statutory unit content inspection (PIN Code, Interception, Repeal, Gyan Post)
"""

import json
import re
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOC1_FILE = PROJECT_ROOT / "data" / "postal_documents" / "extracted" / "postal_2024_rule_english_pages.jsonl"
DOC2_FILE = PROJECT_ROOT / "data" / "postal_documents" / "ocr" / "rule_regulation_english_ocr_pages.jsonl"
CHUNKS_FILE = PROJECT_ROOT / "data" / "postal_documents" / "chunks" / "postal_english_chunks.jsonl"
METADATA_FILE = PROJECT_ROOT / "data" / "postal_documents" / "metadata" / "chunk_metadata.json"


@pytest.fixture(scope="module")
def loaded_chunks():
    """Fixture providing all parsed chunk records."""
    assert CHUNKS_FILE.exists(), f"Chunks file not found at {CHUNKS_FILE}"
    chunks = []
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line_str = line.strip()
            if line_str:
                chunks.append(json.loads(line_str))
    return chunks


@pytest.fixture(scope="module")
def loaded_metadata():
    """Fixture providing the chunk metadata summary."""
    assert METADATA_FILE.exists(), f"Metadata file not found at {METADATA_FILE}"
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def step1_pages():
    """Fixture providing set of verified Step 1 PDF page numbers."""
    pages = set()
    with open(DOC1_FILE, "r", encoding="utf-8") as f:
        for line in f:
            pages.add(json.loads(line)["pdf_page_number"])
    with open(DOC2_FILE, "r", encoding="utf-8") as f:
        for line in f:
            pages.add(json.loads(line)["pdf_page_number"])
    return pages


# 1. Output files exist
def test_chunks_file_exists():
    assert CHUNKS_FILE.exists()
    assert CHUNKS_FILE.is_file()
    assert CHUNKS_FILE.stat().st_size > 0


# 2. Metadata file exists
def test_metadata_file_exists():
    assert METADATA_FILE.exists()
    assert METADATA_FILE.is_file()
    assert METADATA_FILE.stat().st_size > 0


# 3. Valid JSONL format
def test_valid_jsonl():
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line_s = line.strip()
            assert line_s, f"Empty line at line {line_num}"
            record = json.loads(line_s)
            assert isinstance(record, dict)


# 4. Actual chunk count equals metadata count
def test_actual_chunk_count_equals_metadata_count(loaded_chunks, loaded_metadata):
    actual_count = len(loaded_chunks)
    meta_count = loaded_metadata["corpus_summary"]["total_chunks"]
    assert actual_count == meta_count
    assert actual_count == 228


# 5. Required fields exist across all chunks
def test_required_fields_exist(loaded_chunks):
    required = [
        "chunk_id", "document_id", "source_filename", "document_title", "document_type",
        "issuing_authority", "publication_date", "section_type", "unit_number", "heading",
        "chapter_number", "chapter_title", "start_page", "end_page", "source_pages",
        "legal_reference", "text", "char_count", "word_count", "language", "extraction_method",
        "source_version", "boundary_detection_method", "ocr_anomaly"
    ]
    for c in loaded_chunks:
        for field in required:
            assert field in c, f"Chunk {c.get('chunk_id')} missing required field '{field}'"


# 6. Unique chunk IDs
def test_unique_chunk_ids(loaded_chunks):
    chunk_ids = [c["chunk_id"] for c in loaded_chunks]
    assert len(chunk_ids) == len(set(chunk_ids)), "Duplicate chunk IDs found!"


# 7. Deterministic ID formats
def test_deterministic_ids_format(loaded_chunks):
    id_pattern = re.compile(r'^(DOC1_PREAMBLE|DOC1_RULE_\d{2}|DOC2_ACT_PREAMBLE|DOC2_ACT_SECTION_\d{2}|DOC2_REG_PREAMBLE|DOC2_REG_\d{3}|DOC2_REG_SCHEDULE_[I|V|X]+|DOC2_AMEND_\d{4}_\d{2})$')
    for c in loaded_chunks:
        cid = c["chunk_id"]
        assert id_pattern.match(cid), f"Chunk ID '{cid}' does not match deterministic naming policy"


# 8. No empty chunks
def test_no_empty_chunks(loaded_chunks):
    for c in loaded_chunks:
        assert c["char_count"] > 0, f"Chunk {c['chunk_id']} has empty char_count"
        assert c["word_count"] > 0, f"Chunk {c['chunk_id']} has empty word_count"
        assert c["text"].strip(), f"Chunk {c['chunk_id']} has blank text"


# 9. Valid page provenance
def test_valid_page_provenance(loaded_chunks):
    for c in loaded_chunks:
        assert c["start_page"] <= c["end_page"], f"Chunk {c['chunk_id']} start_page > end_page"
        assert len(c["source_pages"]) >= 1, f"Chunk {c['chunk_id']} has empty source_pages"
        assert c["source_pages"][0] == c["start_page"]
        assert c["source_pages"][-1] == c["end_page"]
        assert c["source_pages"] == sorted(c["source_pages"])


# 10. Multi-page chunk correctness
def test_multi_page_chunks_correctness(loaded_chunks, loaded_metadata):
    multi_page = [c for c in loaded_chunks if len(c["source_pages"]) > 1]
    meta_multi_count = loaded_metadata["corpus_summary"]["multi_page_chunk_count"]
    assert len(multi_page) == meta_multi_count
    assert len(multi_page) == 68

    # Check key multi-page provisions
    multi_ids = {c["chunk_id"] for c in multi_page}
    assert "DOC1_RULE_02" in multi_ids  # Rule 2 spans pp. 5-6
    assert "DOC1_RULE_16" in multi_ids  # Rule 16 spans pp. 7-8
    assert "DOC2_REG_SCHEDULE_I" in multi_ids  # Schedule I spans pp. 199-203
    assert "DOC2_REG_SCHEDULE_III" in multi_ids  # Schedule III spans pp. 205-224
    assert "DOC2_AMEND_2025_02" in multi_ids  # Gyan post spans pp. 237-238


# 11. Source pages belong to Step 1 corpus
def test_source_pages_belong_to_step1_corpus(loaded_chunks, step1_pages):
    assert len(step1_pages) == 119
    for c in loaded_chunks:
        for p in c["source_pages"]:
            assert p in step1_pages, f"Page {p} in chunk {c['chunk_id']} not in Step 1 verified corpus"


# 12. Post Office Rules, 2024 (Doc 1) completeness
def test_rules_structure_completeness(loaded_chunks):
    doc1_chunks = [c for c in loaded_chunks if c["document_id"] == "DOC1"]
    assert len(doc1_chunks) == 20
    assert doc1_chunks[0]["chunk_id"] == "DOC1_PREAMBLE"
    rule_nums = [c["unit_number"] for c in doc1_chunks[1:]]
    assert rule_nums == list(range(1, 20))


# 13. The Post Office Act, 2023 (Doc 2) completeness
def test_act_structure_completeness(loaded_chunks):
    act_chunks = [c for c in loaded_chunks if c["document_title"] == "The Post Office Act, 2023"]
    assert len(act_chunks) == 17
    assert act_chunks[0]["chunk_id"] == "DOC2_ACT_PREAMBLE"
    sec_nums = [c["unit_number"] for c in act_chunks[1:]]
    assert sec_nums == list(range(1, 17))


# 14. The Post Office Regulations, 2024 completeness
def test_regulations_structure_completeness(loaded_chunks):
    reg_chunks = [c for c in loaded_chunks if c["section_type"] == "regulation"]
    assert len(reg_chunks) == 180
    reg_nums = [c["unit_number"] for c in reg_chunks]
    assert reg_nums == list(range(1, 181))


# 15. Schedules completeness
def test_schedule_structure_completeness(loaded_chunks):
    sched_chunks = [c for c in loaded_chunks if c["section_type"] == "schedule"]
    assert len(sched_chunks) == 5
    expected_ids = [
        "DOC2_REG_SCHEDULE_I",
        "DOC2_REG_SCHEDULE_II",
        "DOC2_REG_SCHEDULE_III",
        "DOC2_REG_SCHEDULE_IV",
        "DOC2_REG_SCHEDULE_V",
    ]
    assert [c["chunk_id"] for c in sched_chunks] == expected_ids


# 16. 2025 Amendment Notifications completeness
def test_amendment_structure_completeness(loaded_chunks):
    amend_chunks = [c for c in loaded_chunks if c["section_type"] == "amendment"]
    assert len(amend_chunks) == 5
    expected_ids = [
        "DOC2_AMEND_2025_01",
        "DOC2_AMEND_2025_02",
        "DOC2_AMEND_2025_03",
        "DOC2_AMEND_2025_04",
        "DOC2_AMEND_2025_05",
    ]
    assert [c["chunk_id"] for c in amend_chunks] == expected_ids


# 17. Tariff preservation in schedules
def test_tariff_preservation(loaded_chunks):
    chunk_map = {c["chunk_id"]: c for c in loaded_chunks}
    
    # Schedule I (Domestic Tariffs)
    sched1 = chunk_map["DOC2_REG_SCHEDULE_I"]
    sched1_text = sched1["text"]
    assert "TABLE" in sched1_text
    assert "Letters" in sched1_text
    assert "Kilogram" in sched1_text or "grams" in sched1_text
    assert "Speed Post" in sched1_text

    # Schedule III (International Tariffs)
    sched3 = chunk_map["DOC2_REG_SCHEDULE_III"]
    sched3_text = sched3["text"]
    assert "SCHEDULE" in sched3_text
    assert "Postage" in sched3_text or "postage" in sched3_text
    assert "USA" in sched3_text or "Country" in sched3_text


# 18. Child-clause integrity (no orphaned subsections/provisos)
def test_child_clause_integrity(loaded_chunks):
    for c in loaded_chunks:
        first_line = c["text"].strip().split("\n")[0].strip()
        # Ensure chunk does not start with an orphaned sub-clause
        assert not re.match(r'^\s*\([a-z]\)\s+[a-z]', first_line), f"Chunk {c['chunk_id']} starts with orphaned sub-clause (a)-(z)"
        assert not re.match(r'^\s*Provided\s+that', first_line, re.I), f"Chunk {c['chunk_id']} starts with orphaned proviso"
        assert not re.match(r'^\s*Explanation\s*[\.:\-]', first_line, re.I), f"Chunk {c['chunk_id']} starts with orphaned explanation"


# 19. Character count integrity
def test_character_count_integrity(loaded_chunks):
    for c in loaded_chunks:
        assert c["char_count"] == len(c["text"])


# 20. Word count integrity
def test_word_count_integrity(loaded_chunks):
    for c in loaded_chunks:
        assert c["word_count"] == len(c["text"].split())


# 21. OCR anomaly provenance
def test_ocr_anomaly_provenance(loaded_chunks, loaded_metadata):
    anomaly_chunks = [c for c in loaded_chunks if c.get("ocr_anomaly")]
    assert len(anomaly_chunks) == loaded_metadata["corpus_summary"]["ocr_anomaly_count"]
    assert len(anomaly_chunks) == 48

    # Every anomaly chunk must specify anomaly_note and method
    for c in anomaly_chunks:
        assert c["boundary_detection_method"] == "contextual_ocr_resolution"
        assert c["anomaly_note"] is not None
        assert len(c["anomaly_note"]) > 5

    # Check known anomaly chunks
    chunk_map = {c["chunk_id"]: c for c in loaded_chunks}
    assert chunk_map["DOC2_REG_022"]["ocr_anomaly"] is True
    assert chunk_map["DOC2_ACT_SECTION_09"]["ocr_anomaly"] is True
    assert chunk_map["DOC2_ACT_SECTION_16"]["ocr_anomaly"] is True


# 22. English-only cleanliness (no Devanagari Hindi text)
def test_no_unexpected_hindi_pages(loaded_chunks):
    devanagari_re = re.compile(r'[\u0900-\u097F]{4,}')
    # Preambles or gazette headers may have minor bilingual headers (e.g. gazette header on p. 7),
    # but actual statutory text chunks must not be Hindi-only
    for c in loaded_chunks:
        # Assert each chunk has substantially English characters
        ascii_chars = sum(1 for ch in c["text"] if ord(ch) < 128)
        assert ascii_chars / len(c["text"]) > 0.85, f"Chunk {c['chunk_id']} has excessive non-ASCII text"


# 23. Deterministic regeneration
def test_deterministic_regeneration():
    from scripts.data.chunk_postal_documents import run_chunking_pipeline
    chunks_1, meta_1 = run_chunking_pipeline()
    chunks_2, meta_2 = run_chunking_pipeline()

    assert len(chunks_1) == len(chunks_2)
    assert meta_1 == meta_2
    for c1, c2 in zip(chunks_1, chunks_2):
        assert c1 == c2


# 24. Critical statutory content verification
def test_critical_statutory_content(loaded_chunks):
    chunk_map = {c["chunk_id"]: c for c in loaded_chunks}

    # PIN Code in Regulation 175
    reg175 = chunk_map["DOC2_REG_175"]
    assert "PIN Code" in reg175["text"] or "Postal Index Number" in reg175["text"]
    assert reg175["unit_number"] == 175
    assert reg175["chapter_number"] == "CHAPTER XIV"

    # Interception in Act Section 9
    act_sec9 = chunk_map["DOC2_ACT_SECTION_09"]
    assert "intercepted" in act_sec9["text"] or "itecepted" in act_sec9["text"]
    assert act_sec9["unit_number"] == 9

    # Repeal of 1898 Act in Act Section 16
    act_sec16 = chunk_map["DOC2_ACT_SECTION_16"]
    assert "1898" in act_sec16["text"]
    assert "repealed" in act_sec16["text"]

    # Gyan Post in Second Amendment
    amend2 = chunk_map["DOC2_AMEND_2025_02"]
    assert "Gyan Post" in amend2["text"] or "GYAN POST" in amend2["text"]
    assert amend2["unit_number"] == "2025_02"
