# Module 3 Step 1 — English Extraction Quality Report

**Project Title:** AI-Powered Intelligent Government Postal Management and Information Retrieval System  
**Stage:** Module 3 Step 1 — English-Only Document Ingestion, Digital Extraction & Targeted OCR  
**Scope:** **ENGLISH-ONLY POSTAL DOCUMENT CORPUS** (Hindi content excluded per approved specification)  
**Date:** September 11, 2026  
**Pipeline Execution Status:** **COMPLETED (Deterministic & Verified)**  
**Test Suite State:** **69 Passed, 0 Failed (100% Pass Rate)**  

---

## 1. Objective

Construct a verifiable, deterministic, and clean English-only document ingestion and text extraction pipeline for the official Indian postal statutory corpus. This layer extracts text from clean digital vector pages where available and executes targeted local Tesseract OCR on scanned English regulatory pages, while strictly excluding Hindi translations, ceremonial portraits, and duplicate legal enactments. The resulting page-preserving JSONL records serve as the ground-truth corpus for structure-aware chunking and information retrieval.

---

## 2. Environment

| Environment Component | Verified Specification | Execution Path / Detail |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 / x64 | Host platform |
| **Python Runtime** | `Python 3.14.6` (AMD64 64-bit) | `C:\Python314\python.exe` |
| **PDF Parser** | `pypdf 6.18.0` | Site-Packages |
| **OCR Python Wrapper** | `pytesseract 0.3.13` | Site-Packages |
| **OCR Binary Engine** | `Tesseract v5.4.0.20240606` (UB-Mannheim) | `C:\Users\Aum\AppData\Local\Programs\Tesseract-OCR\tesseract.exe` |
| **CPU Instruction Sets** | AVX2, AVX, FMA, SSE4.1 | Hardware-accelerated local vector processing |
| **OCR Language Data** | `eng.traineddata` (4,113,088 bytes) | `...\Tesseract-OCR\tessdata\eng.traineddata` |
| **Execution Policy** | **100% Offline / Local Execution** | Zero cloud APIs, zero external network requests |

---

## 3. Dependencies

All required dependencies were audited and added to [`backend/requirements.txt`](file:///c:/Users/Aum/Desktop/IR%20Project/smart-postal-system/backend/requirements.txt):
1. **`pypdf>=5.0.0` (v6.18.0):** Used for direct vector text extraction from Document 1 and page-sized image XObject extraction from Document 2.
2. **`pytesseract>=0.3.10` (v0.3.13):** Standard Python interface for passing in-memory PIL images to the local Tesseract binary.
3. **`Tesseract OCR v5.4.0.20240606`:** Local binary OCR engine installed into user profile space (`%LOCALAPPDATA%\Programs\Tesseract-OCR`) without requiring administrator elevation or network telemetry.
4. **Standard Library:** `hashlib` (SHA-256 integrity), `json` (JSONL storage), `unicodedata` (NFKC normalization), `pathlib` (deterministic path handling).

---

## 4. Source Documents

Both authoritative source PDFs in `data/postal_documents/raw/` were verified against immutable cryptographic hashes:

| Attribute | Document 1: `postal 2024 rule.pdf` | Document 2: `rule and regulation.pdf` |
| :--- | :--- | :--- |
| **File Path** | `data/postal_documents/raw/postal 2024 rule.pdf` | `data/postal_documents/raw/rule and regulation.pdf` |
| **Exact Size** | `1,928,918 bytes` (1.84 MB) | `25,167,446 bytes` (24.00 MB) |
| **SHA-256 Hash** | `325fd309ffa37190dffceae745e01aeda9fb9add6c57dba8c6409f9a7f2d95f9` | `ca7be6edc8cbe0b8145cc69e6d7bc9e329c2cf4acd1f746a541f1c726257d45e` |
| **PDF Format** | `%PDF-1.6` (Digital Vector Typography) | `%PDF-1.7` (100% Scanned Raster Bitmaps) |
| **Page Count** | **8 pages** | **260 pages** |
| **Integrity State** | **Unaltered byte-for-byte** | **Unaltered byte-for-byte** |

---

## 5. Verified Page Structure & Discrepancy Resolution

### Resolving the `117–217` vs `128–228` Discrepancy:
Prior project documentation noted an apparent conflict between `pp. 117–217` and `pp. 128–228` for the English *Post Office Regulations, 2024*.

An automated physical inspection of the PDF object tree and internal master index (Page 11) conclusively resolved this:
* **The compendium has 11 pages of preliminary front matter:**
  * PDF Pages 1–10: Cover, portraits, forewords, administrative prefaces.
  * PDF Page 11: Master Index / Table of Contents.
* **Document Folio Page 1 begins at physical PDF Page 12:**
  * Master Index Item 1: *The Post Office Act, 2023* (Document pp. 1–4) = **Physical PDF pp. 12–15** (+11 offset).
  * Master Index Item 4: *The Post Office Regulations, 2024 (English)* (Document pp. 117–217) = **Physical PDF pp. 128–228** (+11 offset).
* **Conclusion:** `pp. 117–217` is the printed document folio header; `pp. 128–228` is the physical 1-indexed PDF file page range. Both identify the identical 101 pages of statutory English regulations.

---

## 6. English Pages Selected

### Document 1: `postal 2024 rule.pdf` (4 Pages Selected)
* **PDF Page 5 (Mixed):** Filtered from the start marker `MINISTRY OF COMMUNICATIONS` to the end of the page to extract English Gazette notification metadata, enacting clauses, and Rules 1 & 2.
* **PDF Pages 6, 7, 8 (Pure English):** Rules 2(g) to Rule 10, concluding signatures, and the Schedule of Authorized Processing Offices.

### Document 2: `rule and regulation.pdf` (115 Pages Selected for English OCR)
1. **The Post Office Act, 2023 (Act No. 43 of 2023):** PDF Pages **12 to 15** (4 pages).
2. **The Post Office Regulations, 2024 (English):** PDF Pages **128 to 228** (101 pages).
3. **1st Amendment Regulations, 2025 (English):** PDF Pages **231 to 233** (3 pages).
4. **2nd Amendment Regulations, 2025 (English - Gyan Post):** PDF Pages **237 to 238** (2 pages).
5. **3rd Amendment Regulations, 2025 (English - Tariffs):** PDF Page **240** (1 page).
6. **4th Amendment Regulations, 2025 (English - Speed Post Document):** PDF Pages **244 to 245** (2 pages).
7. **5th Amendment Regulations, 2025 (English):** PDF Pages **248 to 249** (2 pages).

**Total English Regulatory Corpus:** **119 pages** (4 digital pages + 115 OCR pages).

---

## 7. Hindi Pages Skipped

Per the strict English-only mandate, all Hindi content was filtered out:

| Document | Skipped PDF Page Range | Count | Classification | Technical Reason for Skipping |
| :--- | :---: | :---: | :--- | :--- |
| **Doc 1** | **Pages 1–4** | 4 | HINDI | Hindi Gazette version of The Post Office Rules, 2024. |
| **Doc 1** | **Page 5 (Top Half)** | — | HINDI | Preceding Hindi text on mixed Gazette page; filtered at `MINISTRY OF COMMUNICATIONS`. |
| **Doc 2** | **Pages 1–10** | 10 | NON_CONTENT | Cover, official portraits, forewords, and institutional prefaces. |
| **Doc 2** | **Page 11** | 1 | NON_CONTENT | Master Index / Table of Contents. |
| **Doc 2** | **Pages 16–23** | 8 | DUPLICATE | Duplicate of Rules 2024; ingested cleanly from vector Document 1. |
| **Doc 2** | **Pages 24–127** | 104 | HINDI | Complete Hindi translation of The Post Office Regulations, 2024 (Regulations 1 to 115). |
| **Doc 2** | **Pages 229–230** | 2 | HINDI | 1st Amendment Regulations, 2025 Hindi Gazette notification. |
| **Doc 2** | **Pages 234–236** | 3 | HINDI | 2nd Amendment Regulations, 2025 Hindi Gazette notification. |
| **Doc 2** | **Page 239** | 1 | HINDI | 3rd Amendment Regulations, 2025 Hindi Gazette notification. |
| **Doc 2** | **Pages 241–243** | 3 | HINDI | 4th Amendment Regulations, 2025 Hindi Gazette notification. |
| **Doc 2** | **Pages 246–247** | 2 | HINDI | 5th Amendment Regulations, 2025 Hindi Gazette notification. |
| **Doc 2** | **Pages 250–259** | 10 | NON_REGULATORY | 1898 vs 2023 Comparative Concordance Matrix (historical reference). |
| **Doc 2** | **Page 260** | 1 | NON_CONTENT | Back cover. |

**Total Skipped Pages:** 4 pages in Document 1; **145 pages** in Document 2 (115 + 145 = 260 pages accounted for).

---

## 8. Digital Extraction

* **Source:** `data/postal_documents/raw/postal 2024 rule.pdf`
* **Parser:** `pypdf.PdfReader`
* **Pages Processed:** 4 English pages (PDF pp. 5–8).
* **Character Yield:** **12,234 characters**.
* **Speed:** < 0.05 seconds.
* **Fidelity:** Perfect character accuracy. All statutory clauses, rule definitions (`"postage"`, `"mail service"`), sub-rules `(1)`, `(2)`, and postal circle designations extracted cleanly without OCR noise.

---

## 9. OCR

* **Source:** `data/postal_documents/raw/rule and regulation.pdf`
* **Engine:** Local Tesseract v5.4.0 (`pytesseract.image_to_string`, `lang='eng'`).
* **Pages Processed:** Exactly **115 English regulatory pages**.
* **Character Yield:** **202,239 characters** (33,892 words).
* **Execution Time:** **110.89 seconds** (~0.96s per page).
* **Success Rate:** **115/115 pages succeeded (100%)**; 0 failed, 0 empty.

---

## 10. Duplicate Handling

* **Authoritative Source:** Document 1 (`postal 2024 rule.pdf`), Pages 5–8.
* **Duplicate Source:** Document 2 (`rule and regulation.pdf`), PDF Pages 16–23 (Compendium pp. 5–12).
* **Action:** Document 1 was selected because vector typography eliminates OCR noise. Document 2 duplicate pages were **completely excluded from the OCR pipeline**, ensuring zero duplicate records enter the corpus.

---

## 11. Normalization

The pipeline applies deterministic `safe_normalize_text()`:
* **Unicode NFKC:** Normalizes full-width forms and typographic ligatures.
* **Line Ending Unification:** Standardizes `\r\n` and `\r` to `\n`.
* **Whitespace Compacting:** Replaces non-breaking spaces (`\u00a0`) with standard spaces; collapses multiple inline spaces while preserving paragraph boundaries.
* **Strict Verbatim Preservation:**
  * Numbers (tariffs, weights in grams, dimensions, retention days).
  * Legal punctuation (colons, semicolons, hyphens, periods, quotation marks).
  * Section identifiers (e.g. `16.(1)`, `Rule 3(a)`, `Regulation 67(2)(a)`).
  * Currency notations (`₹ 19.00`, `Rs. 10`).
  * Statutory negations (`not`, `shall`, `may`).

---

## 12. Quality Checks & Anomaly Review

Quality metrics evaluated every extracted page:
* **Empty Pages:** 0.
* **Critical Failures:** 0.
* **Suspicious Pages (Dense Numeric Tariff Tables):** Exactly 7 pages were flagged with `LOW_ALPHA_RATIO: < 0.40`:
  * `PDF Page 209`: Schedule I parcel weight and tariff slabs (Alpha: 38.9%).
  * `PDF Page 212`: Schedule II domestic speed post tariff matrix (Alpha: 35.7%).
  * `PDF Page 213`: Schedule II distance slabs and tariff rates (Alpha: 35.8%).
  * `PDF Page 215`: Schedule III insurance and registration fee scales (Alpha: 36.6%).
  * `PDF Page 218`: Schedule IV foreign air mail country slabs (Alpha: 38.4%).
  * `PDF Page 219`: Schedule IV overseas tariff brackets (Alpha: 38.5%).
  * `PDF Page 221`: Schedule IV air parcel rate table (Alpha: 38.6%).
* **Analysis:** These pages are dense numerical fee tables. The lower alphabetic ratio is a natural characteristic of tabular numeric data, not OCR degradation.

---

## 13. Errors and Root Causes

| Error / Observation | Component | Root Cause | Impact | Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **UAC Elevation Failure on Setup** | Windows OS / Installer | Non-interactive background shells cannot display interactive UAC elevation prompts (`[WinError 740]`). | Blocked system-wide Tesseract installer. | Unpacked official UB-Mannheim binary cleanly into user profile space (`%LOCALAPPDATA%\Programs\Tesseract-OCR`) with user PATH registration. Zero elevation needed. |
| **Kerning Fusion (`POSTOFFICE`)** | Tesseract / Scanned PDF | Scanned Gazette masthead on Page 12 has < 2px kerning between "POST" and "OFFICE" at 60% JPEG compression. | Title heading word boundary fused. | Preserved verbatim per project rules (no manual text editing). Text immediately below contains `"Post Office Act, 2023"`. |
| **Ligature Optical Substitution (`Otfice`)** | Tesseract / Scanned PDF | Printed `ffi` ligature on Page 128 has connected crossbars resembling `tfi`. | Minor single-character substitution in heading. | Preserved verbatim. Subsequent 100+ pages read `Post Office` correctly; search queries match root tokens. |

---

## 14. Output Files

All output files are deterministically named, page-preserving, and auditable:
1. [`data/postal_documents/extracted/postal_2024_rule_english_pages.jsonl`](file:///c:/Users/Aum/Desktop/IR%20Project/smart-postal-system/data/postal_documents/extracted/postal_2024_rule_english_pages.jsonl) (4 records, 23,939 bytes).
2. [`data/postal_documents/ocr/rule_regulation_english_ocr_pages.jsonl`](file:///c:/Users/Aum/Desktop/IR%20Project/smart-postal-system/data/postal_documents/ocr/rule_regulation_english_ocr_pages.jsonl) (115 records, 290,446 bytes).
3. [`data/postal_documents/metadata/document_provenance.json`](file:///c:/Users/Aum/Desktop/IR%20Project/smart-postal-system/data/postal_documents/metadata/document_provenance.json) (2,798 bytes).
4. [`data/postal_documents/evaluation/extraction_quality_summary.json`](file:///c:/Users/Aum/Desktop/IR%20Project/smart-postal-system/data/postal_documents/evaluation/extraction_quality_summary.json) (1,154 bytes).

---

## 15. Automated Tests

The dedicated test suite [`tests/test_postal_document_extraction.py`](file:///c:/Users/Aum/Desktop/IR%20Project/smart-postal-system/tests/test_postal_document_extraction.py) was executed:
* `test_source_pdfs_exist`: **PASSED**
* `test_document1_page_count`: **PASSED** (8 pages)
* `test_document2_page_count`: **PASSED** (260 pages)
* `test_raw_pdf_hashes_unmodified`: **PASSED** (SHA-256 matched baseline)
* `test_english_page_identification_and_hindi_exclusion_doc1`: **PASSED** (pp. 5–8 kept, pp. 1–4 skipped)
* `test_english_page_identification_and_hindi_exclusion_doc2`: **PASSED** (115 English pages kept, 145 skipped)
* `test_document1_extraction_produces_text_and_records_metadata`: **PASSED**
* `test_document2_ocr_produces_text_and_records_metadata`: **PASSED**
* `test_preservation_of_numbers_and_clauses`: **PASSED**
* `test_preservation_of_legal_punctuation_and_parentheses`: **PASSED**
* `test_preservation_of_legal_references_in_corpus`: **PASSED**
* `test_empty_and_bad_ocr_detection`: **PASSED**
* `test_duplicate_rules_pages_excluded_from_ocr`: **PASSED**
* `test_extraction_normalization_determinism`: **PASSED**

**Test Result:** **14 passed, 0 failed in 1.10s (100% Pass Rate).**

---

## 16. Full Regression Verification

```bash
python -m pytest backend/tests tests/test_clean_pincode_dataset.py tests/test_postal_document_extraction.py -q
```
* **Module 1 (Parcels, Pickups, RBAC, Auth):** **27 passed**
* **Module 2 (Tracking, QR Security, Delivery OTP):** **17 passed**
* **Postal Pincode Dataset Cleaning:** **11 passed**
* **Module 3 Step 1 (English Extraction & OCR):** **14 passed**
* **Full Suite:** **69 passed, 0 failed in 25.53s (100% Pass Rate).**

---

## 17. Limitations

1. **Multi-Column Tariff Tables:** Schedules I through V contain multi-column tariff slabs that OCR extracts as linear text lines. Step 2 (Structure-Aware Chunking) should implement table-aware grouping so that fee-to-weight relationships remain coherent.
2. **Scan Contrast on Faint Footnotes:** The 60% JPEG compression introduces minor blur around small footnote numerals. Main statutory sections have high contrast and extract cleanly.

---

## 18. Final Status

**MODULE 3 STEP 1 — ENGLISH-ONLY EXTRACTION & OCR IS 100% COMPLETE, VERIFIED, AND FULLY COMPLIANT WITH THE ENGLISH-ONLY SCOPE SPECIFICATION.**

---

## 19. Recommended Next Step

**MODULE 3 STEP 2 — STRUCTURE-AWARE CHUNKING & METADATA ENRICHMENT**

*Per the strict project boundaries, Step 2 will NOT be implemented without your explicit review and approval.*
