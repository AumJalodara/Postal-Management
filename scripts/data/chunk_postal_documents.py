"""scripts/data/chunk_postal_documents.py

Module 3 — Step 2: Structure-Aware Legal Chunking + Metadata Enrichment
AI-Powered Intelligent Government Postal Management and Information Retrieval System

Transforms the verified English page-level corpus produced by Step 1 into
structure-aware legal/postal chunks following the statutory principle:
    ONE COMPLETE LEGAL/POSTAL UNIT = ONE CHUNK

Authoritative Inputs:
    - data/postal_documents/extracted/postal_2024_rule_english_pages.jsonl (Doc 1: 4 pages)
    - data/postal_documents/ocr/rule_regulation_english_ocr_pages.jsonl (Doc 2: 115 pages)

Outputs:
    - data/postal_documents/chunks/postal_english_chunks.jsonl
    - data/postal_documents/metadata/chunk_metadata.json
"""

import sys
import json
import re
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

sys.stdout.reconfigure(encoding="utf-8")

# ==============================================================================
# CONSTANTS AND PATHS
# ==============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOC1_FILE = PROJECT_ROOT / "data" / "postal_documents" / "extracted" / "postal_2024_rule_english_pages.jsonl"
DOC2_FILE = PROJECT_ROOT / "data" / "postal_documents" / "ocr" / "rule_regulation_english_ocr_pages.jsonl"
OUTPUT_CHUNKS_FILE = PROJECT_ROOT / "data" / "postal_documents" / "chunks" / "postal_english_chunks.jsonl"
OUTPUT_METADATA_FILE = PROJECT_ROOT / "data" / "postal_documents" / "metadata" / "chunk_metadata.json"

SCHEMA_VERSION = "1.0.0"

# ==============================================================================
# OCR ANOMALY DEFINITIONS & PATTERNS (DOCUMENT 2 REGULATIONS)
# ==============================================================================

# Specific boundary patterns for regulations where OCR produced known character quirks
# We preserve the raw OCR text unchanged while resolving the structural boundary.
REG_ANOMALY_PATTERNS = {
    22: (re.compile(r'^\s*2\s*,\s*Posting\s+of\s+items', re.I), "OCR dropped first digit 2, appearing as '2, Posting of items.'"),
    35: (re.compile(r'^\s*35\s*[\.,]\s*ems\s+suspected\s+to\s+contain', re.I), "OCR dropped leading 'I' in 'Items', appearing as '35. ems suspected'"),
    50: (re.compile(r'^\s*450\s*,\s*Special\s+procedure', re.I), "OCR prepended margin artifact '4', appearing as '450, Special procedure'"),
    52: (re.compile(r'^\s*52\s+Delivery\s+of\s+damaged', re.I), "OCR omitted delimiter after number, appearing as '52 Delivery of damaged'"),
    61: (re.compile(r'^\s*[\(\[]?61\s*[\.,]\s*Delivery\s+of\s+items\s+on\s+which\s+customs', re.I), "OCR prepended parenthesis '(61. Delivery of items'"),
    62: (re.compile(r'^\s*[\(\[]?62\s+Refusal\s+of\s+items', re.I), "OCR prepended parenthesis and omitted delimiter '(62 Refusal of items'"),
    66: (re.compile(r'^\s*666\s*,\s*Standard\s+remarks', re.I), "OCR duplicated digit 6, appearing as '666, Standard remarks'"),
    72: (re.compile(r'^\s*72\s+Recovery\s+of\s+dues', re.I), "OCR omitted delimiter after number, appearing as '72 Recovery of dues'"),
    77: (re.compile(r'^\s*77\s*[\.,]\s*ems\s+treated\s+as\s+lost', re.I), "OCR dropped leading 'I' in 'Items', appearing as '77. ems treated as lost'"),
    91: (re.compile(r'^\s*[\u2018\u2019\'\"]?91\s*[\.,]\s*Post[ec]ards', re.I), "OCR prepended quote and typo 'Posteards', appearing as '‘91. Posteards'"),
    93: (re.compile(r'^\s*98\s*[\.,]\s*Literature\s+for\s+blind', re.I), "OCR misread '93' as '98' for domestic Literature for Blind on page 164"),
    96: (re.compile(r'^\s*96\s*:\s*India\s+post\s+parcel', re.I), "OCR read colon delimiter, appearing as '96: India post parcel'"),
    102: (re.compile(r'^\s*(?:1102|102)\s*[\.,]\s*Media\s+post', re.I), "OCR prepended margin mark '1', appearing as '1102. Media post'"),
    103: (re.compile(r'^\s*(?:1103|103)\s*[\.,]\s*.*(?:Post|e-Post)', re.I), "OCR prepended margin mark '1', appearing as '1103. c-Post'"),
    104: (re.compile(r'^\s*104\s*[\.,]\s*e-Payment', re.I), "Regulation 104 e-Payment"),
    106: (re.compile(r'^\s*(?:1106|106)\s*[\.,]\s*Magazine\s+post', re.I), "OCR prepended margin mark '1', appearing as '1106, Magazine post'"),
    114: (re.compile(r'^\s*[\u2018\u2019\'\"]?114\s*[\.,]\s*M-Bag', re.I), "OCR prepended quote, appearing as '‘114, M-Bag'"),
    115: (re.compile(r'^\s*[\u2018\u2019\'\"]?1\s*[\.,]\s*Literature\s+for\s+blind\s*\(International\)', re.I), "OCR read '115' as '‘1.' on page 175 for international Literature for blind"),
    123: (re.compile(r'^\s*125\s*[\.,]\s*Other\s+features', re.I), "Gazette misprinted/OCR read 123 as '125, Other features.' on page 179"),
    130: (re.compile(r'^\s*130\s*[\.\(]\s*\(?[0-9\(\)]*', re.I), "OCR condensed heading line, appearing as '130.(0' on page 182"),
    133: (re.compile(r'^\s*(?:138|133)\s*[\.,]\s*Insurance\s+of\s+domestic\s+items', re.I), "OCR read digit '3' as '8', appearing as '138. Insurance of domestic items' on page 183"),
    135: (re.compile(r'^\s*(?:185|135)\s*[\.,]\s*Cash\s+on\s+delivery', re.I), "OCR read '135' as '185, Cash on delivery' on page 184"),
    141: (re.compile(r'^\s*(?:AL|141)\s*[\.,]\s*Redirected\s+or\s+returned\s+international\s+item', re.I), "OCR read '141.' as 'AL,' on page 186"),
    142: (re.compile(r'^\s*(?:1142|142)\s*[\.,]\s*Compensation\s+payable', re.I), "OCR prepended margin mark '1', appearing as '1142. Compensation payable' on page 186"),
    144: (re.compile(r'^\s*(?:14|144)\s*[\.,]\s*Advice\s+of\s+delivery', re.I), "OCR dropped middle digit 4, appearing as '14, Advice of delivery' on page 188"),
    152: (re.compile(r'^\s*(?:1152|152)\s*[\.,]\s*Exemption\s+from\s+liability', re.I), "OCR prepended margin mark '1', appearing as '1152, Exemption from liability' on page 191"),
    153: (re.compile(r'^\s*(?:1153|153)\s*[\.,]\s*Undelivered\s+Money\s+Order', re.I), "OCR prepended margin mark '1', appearing as '1153, Undelivered Money Order' on page 191"),
    154: (re.compile(r'^\s*(?:1154|154)\s*[\.,]\s*Void\s+money\s+order', re.I), "OCR prepended margin mark '1', appearing as '1154, Void money order' on page 191"),
    158: (re.compile(r'^\s*(?:1158|158)\s*[\.,]\s*Currency\s+period', re.I), "OCR prepended margin mark '1', appearing as '1158, Currency period' on page 192"),
    161: (re.compile(r'^\s*(?:61|161)\s*[\.,]\s*Payee\'s\s+name\s+essential', re.I), "OCR dropped leading digit 1, appearing as '61. Payee's name essential' on page 192"),
    162: (re.compile(r'^\s*(?:1162|162)\s*[\.,]\s*Payment\s+through\s+bank', re.I), "OCR prepended margin mark '1', appearing as '1162. Payment through bank' on page 192"),
    164: (re.compile(r'^\s*[\u2018\u2019\'\"]?164\s*[\.,]\s*Mutilated\s+postal\s+orders', re.I), "OCR prepended quote, appearing as '‘164. Mutilated postal orders' on page 193"),
    171: (re.compile(r'^\s*[\u2018\u2019\'\"]?71\s*[\.,]\s*Authority\s+authorised\s+to\s+approve', re.I), "OCR prepended quote and dropped digit 1, appearing as '‘71. Authority' on page 195"),
    174: (re.compile(r'^\s*(?:1174|174)\s*[\.,]\s*Post\s+Office\s+network', re.I), "OCR prepended margin mark '1', appearing as '1174. Post Office network' on page 196"),
}

# CHAPTER TITLES FOR POST OFFICE REGULATIONS, 2024
CHAPTER_MAP = {
    1: ("CHAPTER I", "PRELIMINARY"),
    2: ("CHAPTER I", "PRELIMINARY"),
    3: ("CHAPTER II", "GENERAL"),
    41: ("CHAPTER III", "MANNER OF DELIVERY OF ITEMS"),
    73: ("CHAPTER IV", "COMPENSATION"),
    86: ("CHAPTER V", "GUIDELINES RELATING TO DETECTION AND IMPOUNDING OF COUNTERFEIT CURRENCY"),
    87: ("CHAPTER VI", "DOMESTIC ITEMS AND SERVICES"),
    107: ("CHAPTER VII", "INTERNATIONAL ITEMS AND SERVICES"),
    128: ("CHAPTER VIII", "UNIVERSAL POSTAL SERVICE"),
    129: ("CHAPTER IX", "OFFICIAL CORRESPONDENCE"),
    132: ("CHAPTER X", "VALUE ADDED SERVICES"),
    145: ("CHAPTER XI", "MONEY REMITTANCE SERVICES"),
    170: ("CHAPTER XII", "BUSINESS SOLUTIONS"),
    174: ("CHAPTER XIII", "PRODUCTS AND SERVICES OFFERED THROUGH COLLABORATION"),
    175: ("CHAPTER XIV", "MISCELLANEOUS"),
    179: ("CHAPTER XV", "POSTAL LIFE INSURANCE"),
    180: ("CHAPTER XVI", "FINANCIAL SERVICES"),
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def extract_heading_from_text(first_line: str, default: str = "") -> str:
    """Extract a clean statutory heading from the first line of a legal unit."""
    cleaned = first_line.strip()
    # Strip leading quotes, bullets, or numerals
    cleaned = re.sub(r'^[\u2018\u2019\'\"\(\[]*[0-9]{1,4}[\s\.,\-:]*(?:\([0-9a-zA-Z]+\)[\.,\-]?)?\s*', '', cleaned)
    # Extract up to delimiter '.-' or ' -' or '.' or ':'
    m = re.match(r'^(.*?)(?:\.-|\s+-\s*|\.\s+|\:\s*)', cleaned)
    if m:
        heading = m.group(1).strip()
        if len(heading) > 2:
            return heading
    # Fallback to first line trimmed
    return cleaned[:80].strip() or default


def build_chunk(
    chunk_id: str,
    doc_id: str,
    filename: str,
    title: str,
    doc_type: str,
    authority: str,
    pub_date: str,
    sec_type: str,
    unit_num: Any,
    heading: str,
    chap_num: Optional[str],
    chap_title: Optional[str],
    lines_subset: List[Tuple[int, str]],
    legal_ref: str,
    extraction_method: str = "digital_pypdf",
    boundary_method: str = "statutory_boundary",
    ocr_anomaly: bool = False,
    anomaly_note: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble a structure-aware chunk record with full metadata provenance."""
    text_content = "\n".join(l[1] for l in lines_subset).strip()
    pages_list = sorted(list(set(l[0] for l in lines_subset)))
    start_p = pages_list[0] if pages_list else 0
    end_p = pages_list[-1] if pages_list else 0

    return {
        "chunk_id": chunk_id,
        "document_id": doc_id,
        "source_filename": filename,
        "document_title": title,
        "document_type": doc_type,
        "issuing_authority": authority,
        "publication_date": pub_date,
        "section_type": sec_type,
        "unit_number": unit_num,
        "heading": heading,
        "chapter_number": chap_num,
        "chapter_title": chap_title,
        "start_page": start_p,
        "end_page": end_p,
        "source_pages": pages_list,
        "legal_reference": legal_ref,
        "text": text_content,
        "char_count": len(text_content),
        "word_count": len(text_content.split()),
        "language": "en",
        "extraction_method": extraction_method,
        "source_version": SCHEMA_VERSION,
        "boundary_detection_method": boundary_method,
        "ocr_anomaly": ocr_anomaly,
        "anomaly_note": anomaly_note,
    }

# ==============================================================================
# DOCUMENT 1: POST OFFICE RULES, 2024 CHUNKER
# ==============================================================================

def chunk_doc1(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chunk Document 1: Post Office Rules, 2024 into Preamble + Rules 1-19."""
    pages_sorted = sorted(pages, key=lambda p: p["pdf_page_number"])
    stream: List[Tuple[int, str]] = []
    for p in pages_sorted:
        pnum = p["pdf_page_number"]
        for line in p["text"].split("\n"):
            stream.append((pnum, line))

    doc_meta = {
        "doc_id": "DOC1",
        "filename": "postal 2024 rule.pdf",
        "title": "Post Office Rules, 2024",
        "doc_type": "Rules",
        "authority": "Department of Posts, Ministry of Communications",
        "pub_date": "2024-12-16",
        "extraction_method": "digital_pypdf",
    }

    # Detect rule start line indices: Rule 1 to Rule 19
    rule_re = re.compile(r'^\s*([0-9]{1,2})\.\s+([A-Z].*)')
    rule_starts: List[Tuple[int, int, str, int]] = []  # (stream_idx, rule_num, line_text, pnum)

    for idx, (pnum, line) in enumerate(stream):
        m = rule_re.match(line)
        if m:
            rnum = int(m.group(1))
            expected = len(rule_starts) + 1
            if rnum == expected and rnum <= 19:
                rule_starts.append((idx, rnum, line.strip(), pnum))

    chunks: List[Dict[str, Any]] = []

    # 1. Preamble (Notification header & enacting formula before Rule 1)
    rule1_idx = rule_starts[0][0]
    preamble_lines = stream[:rule1_idx]
    chunks.append(build_chunk(
        chunk_id="DOC1_PREAMBLE",
        doc_id=doc_meta["doc_id"],
        filename=doc_meta["filename"],
        title=doc_meta["title"],
        doc_type=doc_meta["doc_type"],
        authority=doc_meta["authority"],
        pub_date=doc_meta["pub_date"],
        sec_type="preamble",
        unit_num=None,
        heading="Notification and Enacting Formula",
        chap_num=None,
        chap_title=None,
        lines_subset=preamble_lines,
        legal_ref="Post Office Rules, 2024 — Preamble",
        extraction_method=doc_meta["extraction_method"],
        boundary_method="statutory_boundary",
    ))

    # 2. Rules 1 to 19
    for i in range(len(rule_starts)):
        start_idx, rnum, line_text, _ = rule_starts[i]
        end_idx = rule_starts[i + 1][0] if i + 1 < len(rule_starts) else len(stream)
        rule_lines = stream[start_idx:end_idx]
        heading = extract_heading_from_text(line_text, default=f"Rule {rnum}")

        chunks.append(build_chunk(
            chunk_id=f"DOC1_RULE_{rnum:02d}",
            doc_id=doc_meta["doc_id"],
            filename=doc_meta["filename"],
            title=doc_meta["title"],
            doc_type=doc_meta["doc_type"],
            authority=doc_meta["authority"],
            pub_date=doc_meta["pub_date"],
            sec_type="rule",
            unit_num=rnum,
            heading=heading,
            chap_num=None,
            chap_title=None,
            lines_subset=rule_lines,
            legal_ref=f"Post Office Rules, 2024 — Rule {rnum}",
            extraction_method=doc_meta["extraction_method"],
            boundary_method="statutory_boundary",
        ))

    return chunks

# ==============================================================================
# DOCUMENT 2: THE POST OFFICE ACT, 2023 CHUNKER
# ==============================================================================

def chunk_doc2_act(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chunk Document 2 Part A: The Post Office Act, 2023 into Preamble + Sections 1-16."""
    pages_sorted = sorted(pages, key=lambda p: p["pdf_page_number"])
    stream: List[Tuple[int, str]] = []
    for p in pages_sorted:
        pnum = p["pdf_page_number"]
        for line in p["text"].split("\n"):
            stream.append((pnum, line))

    doc_meta = {
        "doc_id": "DOC2",
        "filename": "rule and regulation.pdf",
        "title": "The Post Office Act, 2023",
        "doc_type": "Act",
        "authority": "Ministry of Law and Justice (Legislative Department)",
        "pub_date": "2023-12-24",
        "extraction_method": "tesseract_ocr",
    }

    # Exact boundary matchers for Act 2023 based on OCR verification:
    act_section_matchers = [
        (1, re.compile(r'^\s*1\.[0\(\)]\s*.*(?:Pos\s+OFce|Post\s+Office)', re.I), "Short title and commencement", False, None),
        (2, re.compile(r'^\s*2\s+tn\s+hiv\s+Act|^\s*2\.\s+In\s+this\s+Act', re.I), "Definitions", True, "OCR read '2. In this Act' as '2 tn hiv Act'"),
        (3, re.compile(r'^\s*3\s+[\(\[]?[0-9\(\)]+[\)\]]?\s*Te\s+Post\s+Office|^\s*3\s*\.\s*\(?1?\)?\s*The\s+Post\s+Office', re.I), "Services to be provided by Post Office", True, "OCR read '3. (1) The Post' as '3 (2) Te Post'"),
        (4, re.compile(r'^[“\"\']?4\s+[\(\[]?[0-9\(\)]+[\)\]]?\s*Me\s+Bot\s+Otic|exclusive\s+pie|exclusive\s+privilege', re.I), "Exclusive privilege in respect of postage stamps", True, "OCR read '4. (1) The Post Office' as '“4 (4) Me Bot Otic'"),
        (5, re.compile(r'^[§5]\.[0-9\(\)\w]*\s*Toe\s+Cental|^\s*5\.\s*\(?1?\)?\s*The\s+Central\s+Government.*(?:prescribe|addressing)', re.I), "Standards for addressing and postcodes", True, "OCR read '5. (1)' as '§.(J) Toe Cental'"),
        (6, re.compile(r'^[{\(]?6\s+The\s+Cental\s+Goverment|^\s*6\.\s*The\s+Central\s+Government.*(?:arrangements|foreign)', re.I), "International postal arrangements", True, "OCR read '6. The Central' as '{6 The Cental'"),
        (7, re.compile(r'^\s*7\.[0-9\(\)\w]*\s*Every\s+person|^\s*7\.\s*\(?1?\)?\s*Every\s+person', re.I), "Recovery of charges", True, "OCR read '7. (1)' as '7.44)'"),
        (8, re.compile(r'^\s*8\.\s*The\s+Central\s+Government|^\s*8\.\s*The\s+Central\s+Government.*(?:conlton|official)', re.I), "Official mark", False, None),
        (9, re.compile(r'^\s*9\.[0-9\(\)\w]*\s*The\s+Cental\s+Govern|^\s*9\.\s*\(?1?\)?\s*The\s+Central\s+Government.*(?:intercepted|detained)', re.I), "Interception, detention and disposal of items", True, "OCR read '9. (1)' as '9.41)'"),
        (10, re.compile(r'^\s*(?:0|10)\.[0-9\(\)\w]*\s*Nowwithstantn|^\s*10\.\s*\(?1?\)?\s*Notwithstanding', re.I), "Exemption from liability", True, "OCR read '10. (1) Notwithstanding' as '0.(2) Nowwithstantn'"),
        (11, re.compile(r'^\s*(?:1M|11)\.\s*The\s+Cental\s+Goverment|^\s*11\.\s*The\s+Central\s+Government', re.I), "Delegation of powers", True, "OCR read '11.' as '1M.'"),
        (12, re.compile(r'^\s*12\.\s*The\s+Central\s+Government', re.I), "Power of Central Government to make rules", False, None),
        (13, re.compile(r'^\s*(?:18|13)[\.\-]\s*The\s+Director\s+Genera|^\s*13\.\s*The\s+Director\s+General', re.I), "Power of Director General to make regulations", True, "OCR read '13-' as '18-'"),
        (14, re.compile(r'^\s*14\.\s*Every\s+re\s+or\s+regulation|^\s*14\.\s*Every\s+rule\s+or\s+regulation', re.I), "Laying of rules and regulations before Parliament", False, None),
        (15, re.compile(r'^\s*15\.[0-9\(\)\w]*\s*any\s+culty|^\s*15\.\s*\(?1?\)?\s*If\s+any\s+difficulty', re.I), "Power to remove difficulties", True, "OCR read '15. (1) If any difficulty' as '15.) any culty'"),
        (16, re.compile(r'16\s*[\.,\-]\s*(?:\(1\)\s*|[0-9\(\)]+\s*)?The\s+indian\s+Post\s+Office|16\.\s*\(?1?\)?\s*The\s+Indian\s+Post\s+Office', re.I), "Repeal and savings", True, "OCR read '16. (1)' as 'Aap ot 16,41)'"),
    ]

    sec_starts: List[Tuple[int, int, str, bool, Optional[str]]] = []
    curr_idx = 0
    for snum, pat, heading, is_anomaly, note in act_section_matchers:
        for idx in range(curr_idx, len(stream)):
            if pat.search(stream[idx][1]):
                sec_starts.append((idx, snum, heading, is_anomaly, note))
                curr_idx = idx + 1
                break

    chunks: List[Dict[str, Any]] = []

    # 1. Preamble (Official Gazette header, presidential assent, title, long title)
    sec1_idx = sec_starts[0][0]
    chunks.append(build_chunk(
        chunk_id="DOC2_ACT_PREAMBLE",
        doc_id=doc_meta["doc_id"],
        filename=doc_meta["filename"],
        title=doc_meta["title"],
        doc_type=doc_meta["doc_type"],
        authority=doc_meta["authority"],
        pub_date=doc_meta["pub_date"],
        sec_type="preamble",
        unit_num=None,
        heading="Enacting Formula, Assent and Preamble",
        chap_num=None,
        chap_title=None,
        lines_subset=stream[:sec1_idx],
        legal_ref="The Post Office Act, 2023 — Preamble",
        extraction_method=doc_meta["extraction_method"],
        boundary_method="statutory_boundary",
    ))

    # 2. Sections 1 to 16
    for i in range(len(sec_starts)):
        start_idx, snum, heading, is_anomaly, note = sec_starts[i]
        end_idx = sec_starts[i + 1][0] if i + 1 < len(sec_starts) else len(stream)
        sec_lines = stream[start_idx:end_idx]

        chunks.append(build_chunk(
            chunk_id=f"DOC2_ACT_SECTION_{snum:02d}",
            doc_id=doc_meta["doc_id"],
            filename=doc_meta["filename"],
            title=doc_meta["title"],
            doc_type=doc_meta["doc_type"],
            authority=doc_meta["authority"],
            pub_date=doc_meta["pub_date"],
            sec_type="section",
            unit_num=snum,
            heading=heading,
            chap_num=None,
            chap_title=None,
            lines_subset=sec_lines,
            legal_ref=f"The Post Office Act, 2023 — Section {snum}",
            extraction_method=doc_meta["extraction_method"],
            boundary_method="contextual_ocr_resolution" if is_anomaly else "statutory_boundary",
            ocr_anomaly=is_anomaly,
            anomaly_note=note,
        ))

    return chunks

# ==============================================================================
# DOCUMENT 2: THE POST OFFICE REGULATIONS, 2024 CHUNKER
# ==============================================================================

def chunk_doc2_regulations(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chunk Document 2 Part B: The Post Office Regulations, 2024 into Preamble + Regs 1-180 + Schedules I-V."""
    pages_sorted = sorted(pages, key=lambda p: p["pdf_page_number"])
    
    # Separate Regulations (pp. 128-198) and Schedules (pp. 199-228)
    reg_pages = [p for p in pages_sorted if p["pdf_page_number"] <= 198]
    sched_pages = [p for p in pages_sorted if p["pdf_page_number"] >= 199]

    doc_meta = {
        "doc_id": "DOC2",
        "filename": "rule and regulation.pdf",
        "title": "The Post Office Regulations, 2024",
        "doc_type": "Regulations",
        "authority": "Director General of Postal Services, Department of Posts",
        "pub_date": "2024-12-16",
        "extraction_method": "tesseract_ocr",
    }

    # Reconstruct lines stream for regulations
    stream: List[Tuple[int, str]] = []
    for p in reg_pages:
        pnum = p["pdf_page_number"]
        for line in p["text"].split("\n"):
            stream.append((pnum, line))

    # Pattern for standard regulation header:
    def match_regulation_start(line: str, expected_num: int) -> bool:
        if expected_num in REG_ANOMALY_PATTERNS:
            pat, _ = REG_ANOMALY_PATTERNS[expected_num]
            return bool(pat.search(line))
        pattern = rf'^\s*[\u2018\u2019\'\"]?{expected_num}\s*[\.,\-]\s*(?:\([0-9a-zA-Z]+\)\s*[\.,\-]?\s*)?([A-Z].*)'
        return bool(re.match(pattern, line))

    # Detect all 180 regulations sequentially
    reg_starts: List[Tuple[int, int, str, bool, Optional[str]]] = []
    curr_idx = 0
    for reg_num in range(1, 181):
        found = False
        for idx in range(curr_idx, len(stream)):
            line = stream[idx][1]
            if match_regulation_start(line, reg_num):
                is_anomaly = reg_num in REG_ANOMALY_PATTERNS
                note = REG_ANOMALY_PATTERNS[reg_num][1] if is_anomaly else None
                reg_starts.append((idx, reg_num, line.strip(), is_anomaly, note))
                curr_idx = idx + 1
                found = True
                break
        if not found:
            raise ValueError(f"Structural boundary failure: Could not find Regulation {reg_num} starting search from line {curr_idx}!")

    chunks: List[Dict[str, Any]] = []

    # 1. Preamble (Notification header, S.O. 5440(E), enacting formula before Regulation 1)
    reg1_idx = reg_starts[0][0]
    chunks.append(build_chunk(
        chunk_id="DOC2_REG_PREAMBLE",
        doc_id=doc_meta["doc_id"],
        filename=doc_meta["filename"],
        title=doc_meta["title"],
        doc_type=doc_meta["doc_type"],
        authority=doc_meta["authority"],
        pub_date=doc_meta["pub_date"],
        sec_type="preamble",
        unit_num=None,
        heading="Notification and Enacting Formula",
        chap_num=None,
        chap_title=None,
        lines_subset=stream[:reg1_idx],
        legal_ref="The Post Office Regulations, 2024 — Preamble",
        extraction_method=doc_meta["extraction_method"],
        boundary_method="statutory_boundary",
    ))

    # 2. Regulations 1 to 180
    current_chap_num = "CHAPTER I"
    current_chap_title = "PRELIMINARY"

    for i in range(len(reg_starts)):
        start_idx, rnum, line_text, is_anomaly, note = reg_starts[i]
        end_idx = reg_starts[i + 1][0] if i + 1 < len(reg_starts) else len(stream)
        reg_lines = stream[start_idx:end_idx]

        # Update chapter context if a new chapter began at or prior to this regulation
        for check_rnum, (cnum, ctitle) in CHAPTER_MAP.items():
            if rnum >= check_rnum:
                current_chap_num = cnum
                current_chap_title = ctitle

        heading = extract_heading_from_text(line_text, default=f"Regulation {rnum}")

        chunks.append(build_chunk(
            chunk_id=f"DOC2_REG_{rnum:03d}",
            doc_id=doc_meta["doc_id"],
            filename=doc_meta["filename"],
            title=doc_meta["title"],
            doc_type=doc_meta["doc_type"],
            authority=doc_meta["authority"],
            pub_date=doc_meta["pub_date"],
            sec_type="regulation",
            unit_num=rnum,
            heading=heading,
            chap_num=current_chap_num,
            chap_title=current_chap_title,
            lines_subset=reg_lines,
            legal_ref=f"The Post Office Regulations, 2024 — Regulation {rnum}",
            extraction_method=doc_meta["extraction_method"],
            boundary_method="contextual_ocr_resolution" if is_anomaly else "statutory_boundary",
            ocr_anomaly=is_anomaly,
            anomaly_note=note,
        ))

    # 3. Schedules I to V
    sched_stream: List[Tuple[int, str]] = []
    for p in sched_pages:
        pnum = p["pdf_page_number"]
        for line in p["text"].split("\n"):
            sched_stream.append((pnum, line))

    sched_defs = [
        ("DOC2_REG_SCHEDULE_I", "I", "SCHEDULE I", "POSTAGE AND FEE FOR DOMESTIC ITEMS", re.compile(r'POSTAGE\s+AND\s+FEE\s+FOR\s+DOMESTIC|SCHEDULE\s*[IT1]', re.I), False, None),
        ("DOC2_REG_SCHEDULE_II", "II", "SCHEDULE II", "POSTAGE AND FEE FOR OTHER POSTAL ITEMS", re.compile(r'POSTAGE\s+AND\s+FEE\s+FOR\s+OTHER\s+POSTAL|SCHEDULE\s*I{2}', re.I), False, None),
        ("DOC2_REG_SCHEDULE_III", "III", "SCHEDULE III", "POSTAGE AND FEE FOR INTERNATIONAL ITEMS", re.compile(r'POSTAGE\s+AND\s+F[EF]{2}\s+FOR\s+INTERNATIONAL|SCHEDULE\s*(?:III|IT|IL)', re.I), True, "OCR read 'SCHEDULE III' as 'SCHEDULE IT' on page 205"),
        ("DOC2_REG_SCHEDULE_IV", "IV", "SCHEDULE IV", "VALUE ADDED SERVICES", re.compile(r'VALUE\s+ADDED\s+SERVICES|SCHEDULE\s*(?:IV|TV)', re.I), True, "OCR read 'SCHEDULE IV' as 'SCHEDULE TV' on page 225"),
        ("DOC2_REG_SCHEDULE_V", "V", "SCHEDULE V", "MONEY REMITTANCE SERVICES", re.compile(r'MONEY\s+REMITTANCE\s+SERVICES|SCHEDULE\s*V\b', re.I), False, None),
    ]

    sched_starts: List[Tuple[int, str, str, str, str, bool, Optional[str]]] = []
    s_curr = 0
    for cid, s_num, s_hdr, s_title, pat, is_anomaly, note in sched_defs:
        for idx in range(s_curr, len(sched_stream)):
            if pat.search(sched_stream[idx][1]):
                sched_starts.append((idx, cid, s_num, s_hdr, s_title, is_anomaly, note))
                s_curr = idx + 1
                break

    if len(sched_starts) != 5:
        raise ValueError(f"Schedule detection error: Expected 5 schedules, found {len(sched_starts)}!")

    for i in range(len(sched_starts)):
        start_idx, cid, s_num, s_hdr, s_title, is_anomaly, note = sched_starts[i]
        end_idx = sched_starts[i + 1][0] if i + 1 < len(sched_starts) else len(sched_stream)
        s_lines = sched_stream[start_idx:end_idx]

        chunks.append(build_chunk(
            chunk_id=cid,
            doc_id=doc_meta["doc_id"],
            filename=doc_meta["filename"],
            title=doc_meta["title"],
            doc_type=doc_meta["doc_type"],
            authority=doc_meta["authority"],
            pub_date=doc_meta["pub_date"],
            sec_type="schedule",
            unit_num=s_num,
            heading=f"{s_hdr}: {s_title}",
            chap_num=None,
            chap_title=None,
            lines_subset=s_lines,
            legal_ref=f"The Post Office Regulations, 2024 — {s_hdr}",
            extraction_method=doc_meta["extraction_method"],
            boundary_method="contextual_ocr_resolution" if is_anomaly else "statutory_boundary",
            ocr_anomaly=is_anomaly,
            anomaly_note=note,
        ))

    return chunks

# ==============================================================================
# DOCUMENT 2: 2025 AMENDMENT NOTIFICATIONS CHUNKER
# ==============================================================================

def chunk_doc2_amendments(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chunk Document 2 Part C: 2025 Amendment Regulations into coherent gazette notification chunks."""
    # Group pages by their Section field from Step 1
    amend_groups: Dict[str, List[Dict[str, Any]]] = {}
    for p in pages:
        sec = p.get("section", "")
        if "Amendment" in sec:
            amend_groups.setdefault(sec, []).append(p)

    # Sort groups in chronological order based on starting page
    sorted_groups = sorted(amend_groups.items(), key=lambda item: min(p["pdf_page_number"] for p in item[1]))

    amendment_configs = [
        {
            "id": "DOC2_AMEND_2025_01",
            "number": "2025_01",
            "title": "Post Office (Amendment) Regulations, 2025 (1st Amendment)",
            "pub_date": "2025-03-28",
            "heading": "Post Office (Amendment) Regulations, 2025 — First Amendment (Tariffs & Schedules)",
            "legal_ref": "Post Office (Amendment) Regulations, 2025 (S.O. 1523(E), 28th March 2025)",
        },
        {
            "id": "DOC2_AMEND_2025_02",
            "number": "2025_02",
            "title": "Post Office (Second Amendment) Regulations, 2025 (Gyan Post)",
            "pub_date": "2025-04-28",
            "heading": "Post Office (Second Amendment) Regulations, 2025 — Gyan Post (Regulation 98A & Tariffs)",
            "legal_ref": "Post Office (Second Amendment) Regulations, 2025 (S.O. 2636(E), 28th April 2025)",
        },
        {
            "id": "DOC2_AMEND_2025_03",
            "number": "2025_03",
            "title": "Post Office (Third Amendment) Regulations, 2025 (Tariffs)",
            "pub_date": "2025-06-19",
            "heading": "Post Office (Third Amendment) Regulations, 2025 — Tariffs Amendment",
            "legal_ref": "Post Office (Third Amendment) Regulations, 2025 (S.O. 2738(E), 19th June 2025)",
        },
        {
            "id": "DOC2_AMEND_2025_04",
            "number": "2025_04",
            "title": "Post Office (Fourth Amendment) Regulations, 2025 (Speed Post Document)",
            "pub_date": "2025-09-25",
            "heading": "Post Office (Fourth Amendment) Regulations, 2025 — Speed Post Document (Table IV A)",
            "legal_ref": "Post Office (Fourth Amendment) Regulations, 2025 (S.O. 4375(E), 25th September 2025)",
        },
        {
            "id": "DOC2_AMEND_2025_05",
            "number": "2025_05",
            "title": "Post Office (Fifth Amendment) Regulations, 2025",
            "pub_date": "2025-10-28",
            "heading": "Post Office (Fifth Amendment) Regulations, 2025 — Schedule III Tariffs",
            "legal_ref": "Post Office (Fifth Amendment) Regulations, 2025 (S.O. 4907(E), 28th October 2025)",
        },
    ]

    chunks: List[Dict[str, Any]] = []

    for idx, (sec_name, p_list) in enumerate(sorted_groups):
        cfg = amendment_configs[idx]
        p_list_sorted = sorted(p_list, key=lambda p: p["pdf_page_number"])
        stream: List[Tuple[int, str]] = []
        for p in p_list_sorted:
            pnum = p["pdf_page_number"]
            for line in p["text"].split("\n"):
                stream.append((pnum, line))

        chunks.append(build_chunk(
            chunk_id=cfg["id"],
            doc_id="DOC2",
            filename="rule and regulation.pdf",
            title=cfg["title"],
            doc_type="Amendment Regulations",
            authority="Director General of Postal Services, Department of Posts",
            pub_date=cfg["pub_date"],
            sec_type="amendment",
            unit_num=cfg["number"],
            heading=cfg["heading"],
            chap_num=None,
            chap_title=None,
            lines_subset=stream,
            legal_ref=cfg["legal_ref"],
            extraction_method="tesseract_ocr",
            boundary_method="statutory_boundary",
            ocr_anomaly=False,
            anomaly_note=None,
        ))

    return chunks

# ==============================================================================
# PIPELINE ORCHESTRATION & VALIDATION
# ==============================================================================

def run_chunking_pipeline() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Execute the full structure-aware chunking pipeline with validation."""
    print("=" * 70)
    print("MODULE 3 STEP 2: STRUCTURE-AWARE LEGAL CHUNKING PIPELINE")
    print("=" * 70)

    # 1. Ingestion & Validation of Step 1 Inputs
    if not DOC1_FILE.exists():
        raise FileNotFoundError(f"Missing Step 1 input: {DOC1_FILE}")
    if not DOC2_FILE.exists():
        raise FileNotFoundError(f"Missing Step 1 input: {DOC2_FILE}")

    with open(DOC1_FILE, "r", encoding="utf-8") as f:
        doc1_records = [json.loads(line) for line in f]
    with open(DOC2_FILE, "r", encoding="utf-8") as f:
        doc2_records = [json.loads(line) for line in f]

    print(f"Loaded Doc 1 records: {len(doc1_records)} pages (expected 4)")
    print(f"Loaded Doc 2 records: {len(doc2_records)} pages (expected 115)")
    total_input_pages = len(doc1_records) + len(doc2_records)
    if total_input_pages != 119:
        raise ValueError(f"Expected exactly 119 input pages, found {total_input_pages}!")

    # 2. Process Document 1 (Rules 2024)
    doc1_chunks = chunk_doc1(doc1_records)
    print(f"Doc 1 generated: {len(doc1_chunks)} chunks (1 Preamble + 19 Rules)")

    # 3. Process Document 2 Part A (Act 2023)
    act_pages = [p for p in doc2_records if p.get("section") == "The Post Office Act, 2023"]
    act_chunks = chunk_doc2_act(act_pages)
    print(f"Doc 2 Act generated: {len(act_chunks)} chunks (1 Preamble + 16 Sections)")

    # 4. Process Document 2 Part B (Regulations 2024)
    reg_pages = [p for p in doc2_records if p.get("section") == "The Post Office Regulations, 2024"]
    reg_chunks = chunk_doc2_regulations(reg_pages)
    print(f"Doc 2 Regulations generated: {len(reg_chunks)} chunks (1 Preamble + 180 Regs + 5 Schedules)")

    # 5. Process Document 2 Part C (Amendments 2025)
    amend_pages = [p for p in doc2_records if "Amendment" in p.get("section", "")]
    amend_chunks = chunk_doc2_amendments(amend_pages)
    print(f"Doc 2 Amendments generated: {len(amend_chunks)} chunks (5 Gazette Notifications)")

    # Combine all chunks
    all_chunks = doc1_chunks + act_chunks + reg_chunks + amend_chunks
    print(f"\nGrand Total Chunks: {len(all_chunks)}")

    # 6. Rigorous Pipeline Validation
    validate_chunks(all_chunks, doc1_records, doc2_records)

    # 7. Compute Corpus Metadata Statistics
    metadata = compute_chunk_metadata(all_chunks, len(doc1_records), len(doc2_records))

    # 8. Write Deterministic Outputs
    OUTPUT_CHUNKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_CHUNKS_FILE, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"Written: {OUTPUT_CHUNKS_FILE} ({OUTPUT_CHUNKS_FILE.stat().st_size:,} bytes)")

    with open(OUTPUT_METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"Written: {OUTPUT_METADATA_FILE} ({OUTPUT_METADATA_FILE.stat().st_size:,} bytes)")

    print("Pipeline completed successfully!")
    return all_chunks, metadata


def validate_chunks(chunks: List[Dict[str, Any]], doc1_pages: List[Dict[str, Any]], doc2_pages: List[Dict[str, Any]]) -> None:
    """Run comprehensive integrity and structural validation checks."""
    print("\nRunning structural validation checks...")

    # A. Check for uniqueness of chunk IDs
    chunk_ids = [c["chunk_id"] for c in chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        duplicates = [cid for cid in chunk_ids if chunk_ids.count(cid) > 1]
        raise ValueError(f"Validation failed: Duplicate chunk IDs detected: {set(duplicates)}")

    # B. Required fields check
    required_fields = [
        "chunk_id", "document_id", "source_filename", "document_title", "document_type",
        "issuing_authority", "publication_date", "section_type", "unit_number", "heading",
        "chapter_number", "chapter_title", "start_page", "end_page", "source_pages",
        "legal_reference", "text", "char_count", "word_count", "language", "extraction_method",
        "source_version", "boundary_detection_method", "ocr_anomaly"
    ]
    for idx, c in enumerate(chunks):
        for field in required_fields:
            if field not in c:
                raise ValueError(f"Validation failed: Chunk {c.get('chunk_id', idx)} missing required field '{field}'!")
        if not c["text"].strip():
            raise ValueError(f"Validation failed: Empty text in chunk {c['chunk_id']}!")
        if c["char_count"] != len(c["text"]):
            raise ValueError(f"Validation failed: char_count mismatch in chunk {c['chunk_id']}!")
        if c["word_count"] != len(c["text"].split()):
            raise ValueError(f"Validation failed: word_count mismatch in chunk {c['chunk_id']}!")
        if c["start_page"] > c["end_page"]:
            raise ValueError(f"Validation failed: start_page > end_page in chunk {c['chunk_id']}!")
        if not c["source_pages"] or c["source_pages"][0] != c["start_page"] or c["source_pages"][-1] != c["end_page"]:
            raise ValueError(f"Validation failed: Page range mismatch in chunk {c['chunk_id']}!")

    # C. Validate source page coverage (all input pages represented)
    covered_doc1_pages = set()
    covered_doc2_pages = set()
    for c in chunks:
        if c["document_id"] == "DOC1":
            covered_doc1_pages.update(c["source_pages"])
        else:
            covered_doc2_pages.update(c["source_pages"])

    input_doc1_pages = set(p["pdf_page_number"] for p in doc1_pages)
    input_doc2_pages = set(p["pdf_page_number"] for p in doc2_pages)

    if covered_doc1_pages != input_doc1_pages:
        missing = input_doc1_pages - covered_doc1_pages
        raise ValueError(f"Validation failed: Doc 1 pages not covered in chunks: {missing}")
    if covered_doc2_pages != input_doc2_pages:
        missing = input_doc2_pages - covered_doc2_pages
        raise ValueError(f"Validation failed: Doc 2 pages not covered in chunks: {missing}")

    print("All structural validation checks passed successfully!")


def compute_chunk_metadata(chunks: List[Dict[str, Any]], doc1_page_count: int, doc2_page_count: int) -> Dict[str, Any]:
    """Compute corpus-level statistical and structural metadata."""
    char_counts = [c["char_count"] for c in chunks]
    word_counts = [c["word_count"] for c in chunks]
    multi_page_chunks = [c["chunk_id"] for c in chunks if len(c["source_pages"]) > 1]
    anomaly_chunks = [c["chunk_id"] for c in chunks if c.get("ocr_anomaly")]

    by_doc: Dict[str, int] = {}
    by_title: Dict[str, int] = {}
    by_type: Dict[str, int] = {}

    for c in chunks:
        by_doc[c["document_id"]] = by_doc.get(c["document_id"], 0) + 1
        by_title[c["document_title"]] = by_title.get(c["document_title"], 0) + 1
        by_type[c["section_type"]] = by_type.get(c["section_type"], 0) + 1

    return {
        "pipeline_step": "Module 3 — Step 2: Structure-Aware Legal Chunking + Metadata Enrichment",
        "schema_version": SCHEMA_VERSION,
        "input_provenance": {
            "doc1_file": DOC1_FILE.relative_to(PROJECT_ROOT).as_posix(),
            "doc1_page_count": doc1_page_count,
            "doc2_file": DOC2_FILE.relative_to(PROJECT_ROOT).as_posix(),
            "doc2_page_count": doc2_page_count,
            "total_source_pages": doc1_page_count + doc2_page_count,
        },
        "output_provenance": {
            "chunks_file": OUTPUT_CHUNKS_FILE.relative_to(PROJECT_ROOT).as_posix(),
            "metadata_file": OUTPUT_METADATA_FILE.relative_to(PROJECT_ROOT).as_posix(),
        },
        "corpus_summary": {
            "total_chunks": len(chunks),
            "chunks_by_document": by_doc,
            "chunks_by_document_title": by_title,
            "chunks_by_section_type": by_type,
            "multi_page_chunk_count": len(multi_page_chunks),
            "multi_page_chunk_ids": multi_page_chunks,
            "ocr_anomaly_count": len(anomaly_chunks),
            "ocr_anomaly_chunk_ids": anomaly_chunks,
        },
        "statistical_profile": {
            "characters": {
                "min": min(char_counts),
                "max": max(char_counts),
                "mean": round(statistics.mean(char_counts), 2),
                "median": statistics.median(char_counts),
                "total": sum(char_counts),
            },
            "words": {
                "min": min(word_counts),
                "max": max(word_counts),
                "mean": round(statistics.mean(word_counts), 2),
                "median": statistics.median(word_counts),
                "total": sum(word_counts),
            }
        },
        "validation_status": "VERIFIED_PASS",
    }


if __name__ == "__main__":
    run_chunking_pipeline()
