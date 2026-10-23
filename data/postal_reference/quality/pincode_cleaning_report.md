# Government Postal Reference Dataset: Cleaning & Normalization Audit Report

**Execution Timestamp:** 2026-09-10 23:47:53
**Pipeline Status:** SUCCESS (Deterministic, Audited)

---

## A. Input / Output Files

- **Raw Authoritative Input:** `data\postal_reference\raw\gov dataset.csv` (Read-only, Unmodified)
- **Cleaned Output Dataset:** `data\postal_reference\processed\postal_reference_cleaned.csv` (UTF-8, RFC 4180 Comma Delimited)
- **Quality Audit Report:** `data/postal_reference/quality/pincode_cleaning_report.md`
- **Reproducibility Script:** `scripts/data/clean_pincode_dataset.py`

## B. Original Row Count
**165,627** data rows (excluding 1 header row).

## C. Processed Row Count
**165,625** data rows (excluding 1 header row).

## D. Number of Exact Duplicate Rows Removed
**2** exact duplicate row(s) removed.

### Details of Removed Duplicate Rows:
- **Source Line 77168:** `['Maharashtra Circle', 'Navi Mumbai Region', 'Malegaon Division', 'Talwade B.O', '423101', 'BO', 'Delivery', 'NASHIK', 'MAHARASHTRA', '20.329957', '74.24379']`
- **Source Line 148133:** `['Madhya Pradesh Circle', 'DivReportingCircle', 'Vidisha Division', 'Bankhedi B.O', '464573', 'BO', 'Delivery', 'RAISEN', 'MADHYA PRADESH', '22.7690540', '78.5348560']`

## E & F. Missing-Value Counts Before and After Cleaning

| Column Name | Raw Missing Count | Raw Missing % | Cleaned Missing Count | Cleaned Missing % | Cleaning Action Taken |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `circlename` | 0 | 0.000% | 0 | 0.000% | Whitespace stripped; complete data preserved |
| `regionname` | 315 | 0.190% | 315 | 0.190% | Whitespace stripped; literal 'NA' converted to empty string |
| `divisionname` | 0 | 0.000% | 0 | 0.000% | Whitespace stripped; complete data preserved |
| `officename` | 0 | 0.000% | 0 | 0.000% | Whitespace trimmed (15 rows had leading/trailing spaces) |
| `pincode` | 0 | 0.000% | 0 | 0.000% | Whitespace stripped; complete data preserved |
| `officetype` | 0 | 0.000% | 0 | 0.000% | Whitespace stripped; complete data preserved |
| `delivery` | 0 | 0.000% | 0 | 0.000% | Whitespace stripped; complete data preserved |
| `district` | 715 | 0.432% | 715 | 0.432% | Whitespace stripped; literal 'NA' converted to empty string |
| `statename` | 715 | 0.432% | 715 | 0.432% | Whitespace stripped; literal 'NA' converted to empty string |
| `latitude` | 12,007 | 7.249% | 12,201 | 7.367% | Whitespace stripped; missing/out-of-range set to empty string |
| `longitude` | 12,002 | 7.246% | 12,057 | 7.280% | Whitespace stripped; missing/out-of-range set to empty string |

## G. PIN-Code Validation Results

- **Total Non-Null PINs Evaluated:** 165,625
- **Valid 6-digit Numeric PINs:** 165,625 (100.0%)
- **Invalid PIN Formats Detected:** 0
- **Leading Zero Preservation:** Successfully preserved (e.g. Northern Circles `11xxxx`, `12xxxx`).
- **PIN String Type:** Preserved as text strings; no numeric truncation or float casting.

## H. Coordinate Transformations & Changes

Total coordinate positions evaluated: **331,250** (165,625 Latitude + 165,625 Longitude).

### Coordinate Classification Summary

| Classification Category | Latitude Count | Longitude Count | Combined Count | % of All Coordinate Slots |
| :--- | :---: | :---: | :---: | :---: |
| **1. Already Valid Numeric Coordinates** | 153,418 | 153,562 | 306,980 | 92.673% |
| **2. Safely Normalized Formatting Issues** | 6 | 6 | 12 | 0.004% |
| **3. Set to Null (Total)** | 12,201 | 12,057 | 24,258 | 7.323% |
| &nbsp;&nbsp;&nbsp;&nbsp;↳ *From literal missing sentinels ('NA')* | 12,007 | 12,002 | 24,009 | 7.248% |
| &nbsp;&nbsp;&nbsp;&nbsp;↳ *From out-of-range (>90° lat or >180° lon)* | 194 | 55 | 249 | 0.075% |

### All 12 Safely Normalized Coordinate Values (6 Records)

| Source Line | Office Name | PIN Code | Coordinate Type | Raw String Value | Normalized Value | Normalization Rule Applied |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| 38791 | Mubaraspur B.O | 502247 | Latitude | `17°57'17.7` | `17.9549167` | `normalized_dms` |
| 38791 | Mubaraspur B.O | 502247 | Longitude | `78°35'48.3` | `78.59675` | `normalized_dms` |
| 99245 | Integrated District Officers Complex(IDOC) Mancher | 504302 | Latitude | `18.856818°` | `18.856818` | `normalized_format` |
| 99245 | Integrated District Officers Complex(IDOC) Mancher | 504302 | Longitude | `79.462604°` | `79.462604` | `normalized_format` |
| 109143 | PYALA BO | 121004 | Latitude | `28.430354° N` | `28.430354` | `normalized_format` |
| 109143 | PYALA BO | 121004 | Longitude | `77.358526° E` | `77.358526` | `normalized_format` |
| 113104 | Legi | 791101 | Latitude | `28.4 32628` | `28.432628` | `normalized_whitespace` |
| 113104 | Legi | 791101 | Longitude | `94.28 28092` | `94.2828092` | `normalized_whitespace` |
| 144391 | Longliang | 792130 | Latitude | `26.52 12743` | `26.5212743` | `normalized_whitespace` |
| 144391 | Longliang | 792130 | Longitude | `95.30 54302` | `95.3054302` | `normalized_whitespace` |
| 161451 | Daniyawan SO | 801308 | Latitude | `25.43 N` | `25.43` | `normalized_format` |
| 161451 | Daniyawan SO | 801308 | Longitude | `85.29 E` | `85.29` | `normalized_format` |

### Representative Out-of-Range Coordinates Set to Null

| Source Line | Office Name | PIN Code | Coordinate Type | Raw Value | Validation Failure Cause |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 4810 | Aideopukhuri B.O | 785690 | Latitude | `94.6318889` | `latitude > 90 or < -90` |
| 7096 | Udari BO | 497101 | Latitude | `23724.290000000001` | `latitude > 90 or < -90` |
| 7356 | Bachhunchh BO | 171207 | Latitude | `331.2000000` | `latitude > 90 or < -90` |
| 7636 | Hardtour BO | 192201 | Latitude | `129.6000000` | `latitude > 90 or < -90` |
| 7637 | Hiller Arahama BO | 192201 | Latitude | `129.6000000` | `latitude > 90 or < -90` |
| 7096 | Udari BO | 497101 | Longitude | `832015.52000000002` | `longitude > 180 or < -180` |
| 7649 | Hiller Shahabad BO | 192211 | Longitude | `284.2000000` | `longitude > 180 or < -180` |
| 7658 | Malwan BO | 192231 | Longitude | `195.3000000` | `longitude > 180 or < -180` |
| 7665 | Tahaba Shadipora BO | 192301 | Longitude | `195.3000000` | `longitude > 180 or < -180` |
| 7691 | Rangar BO | 191113 | Longitude | `3256.1000000` | `longitude > 180 or < -180` |

## I. Records Requiring Manual / Domain Validation

Per project guidelines, these anomalies reflect real-world postal geography and data collection artifacts. They were **not automatically altered** or guessed, and are flagged for India Post domain expert review:

1. **Cross-State PIN Codes (52 PINs):**
   - PIN codes mapping to multiple states (e.g. `506003`, `505325` between Telangana and Andhra Pradesh following state bifurcation; or PINs with state `'NA'` alongside actual state name).
2. **Cross-District PIN Codes (1,258 PINs):**
   - Delivery beats naturally crossing administrative revenue district boundaries.
3. **Shared Office Names (11,076 Names):**
   - Identical rural post office names (e.g. `Rampur B.O`, `Shivpur B.O`) occurring in multiple districts.
4. **Asymmetric Coordinate Pairs (208 Records):**
   - Records where only one coordinate (either latitude or longitude) was recorded.
5. **Coordinates Outside Indian Territorial Bounds (2,377 Records):**
   - Coordinates that are mathematically valid within `[-90, 90]` and `[-180, 180]`, but fall outside India's geographic bounding box (`[6.0, 38.5]` N, `[68.0, 98.0]` E).
   - *Root causes identified:* Transposed/swapped latitude and longitude (e.g. Row 47 `lat=79.0, lon=17.0` for Telangana), unscaled decimals within 90, and `(0.0, 0.0)` unmapped facility placeholders.

## J. Exact Cleaning Rules Applied

1. **Exact Full-Row Deduplication:** Only identical rows across all 11 columns were removed (2 duplicate rows removed).
2. **Whitespace Stripping:** Leading and trailing whitespace was stripped from all fields (resolving 15 unstripped office names).
3. **Missing Sentinel Normalization:** Literal values `NA`, `N/A`, `NULL`, and empty strings were normalized to empty CSV fields `""`.
4. **Semantic Preservation:** Administrative names, district names, state names, circle names, and office names were preserved verbatim without casing shifts, fuzzy matching, or substitution.
5. **PIN Code String Integrity:** Validated 6-digit numeric pattern; preserved as text strings with leading zeroes intact.
6. **Deterministic Coordinate Normalization:**
   - Degrees/Minutes/Seconds (`deg° min' sec"`) converted via $\text{deg} + \frac{\text{min}}{60} + \frac{\text{sec}}{3600}$.
   - Trailing degree symbols `°` stripped.
   - Cardinal directions (`N`, `S`, `E`, `W`) parsed with negative sign for S and W.
   - Internal whitespace between decimal digits (`28.4 32628` -> `28.432628`) removed.
7. **Geodetic Range Validation:** Coordinates outside $[-90, 90]$ for latitude or outside $[-180, 180]$ for longitude were converted to null.
8. **Record Retention:** Records with missing or nulled coordinates were preserved.

## K. Explicit Audit & Compliance Statement

- **The raw authoritative dataset (`gov dataset.csv`) was NOT modified, overwritten, renamed, moved, or deleted.**
- **No external data sources or APIs were used for silent correction.**
- **No records were deleted from the dataset except the 2 exact full-row duplicates.**
- **No geographic coordinates were invented, guessed, or inferred from external geography.**
- **No administrative or jurisdictional conflicts (cross-state/cross-district PINs) were automatically resolved.**
- **Modules 1 and 2 code, database models, migrations, and test suites remain untouched and functional.**
