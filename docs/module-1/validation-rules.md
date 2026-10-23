# Module 1: Validation Rules & Matrix

Every input field is governed by domain-specific semantic rules across all architectural layers.

---

## 1. Validation Matrix

| Field | Category | Layer Rules | Accepted Samples | Rejected Samples | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Name** (Citizen, Receiver) | Text | Unicode letters, spaces, optional single period for initials. Length: 2 to 100 characters. Trimmed and collapsed whitespace. | `Rahul Kumar`<br>`Priya Sharma`<br>`A. Kumar`<br>`Mohammed Ali` | `Rahul123`<br>`12345`<br>`@@Rahul`<br>`Priya_Sharma`<br>`R` | Rejects numbers and special symbols while supporting legitimate Indian names and initials. |
| **Mobile Number** | Numeric String | 10-digit Indian mobile starting with 6, 7, 8, or 9 (`^[6-9]\d{9}$`). Normalized from `+91` or `0` prefix. | `9876543210`<br>`7012345678` | `98765`<br>`98765432101`<br>`abcdefghij`<br>`98765abc10`<br>`5876543210` | Stored canonically as a 10-digit identifier without arbitrary punctuation. |
| **Email** | Identifier | RFC-5322 standard syntax, normalized to lowercase, max 255 chars. Unique constraint in database. | `user@example.com`<br>`rahul.kumar@post.in` | `user`<br>`user@`<br>`@example.com`<br>`user@@example.com` | Prevents malformed emails and ensures unique citizen credentials. |
| **PIN Code** | Identifier | Exactly 6 numeric digits starting with 1–9 (`^[1-9][0-9]{5}$`). Stored as string. | `600001`<br>`110001`<br>`400001` | `60001`<br>`6000012`<br>`ABC123`<br>`60000A`<br>`010001` | Indian PIN codes do not start with 0 and must not be treated as mathematical integers. |
| **Address** | Text | Letters, numbers, spaces, commas, periods, hyphens, slashes, brackets. Min 10, max 300 chars. Reject non-trivial repetitions. | `12/4 Gandhi Street, Near Bus Stand` | `aaaa`<br>`123`<br>`!!!`<br>`Short` | Ensures meaningful address length and presence of recognizable street letters. |
| **Weight** | Numeric | Decimal/Numeric, strictly `> 0.00` and `<= 50.00` kg. Maximum 2 decimal places. | `0.5`<br>`1`<br>`2.5`<br>`10` | `0`<br>`-2`<br>`abc`<br>`55.0` | Prevents zero/negative weight and restricts parcel size to prototype limit. |
| **Parcel Type** | Enum | Must be one of `DOCUMENT`, `SMALL_PARCEL`, `MEDIUM_PARCEL`, `LARGE_PARCEL`. | `DOCUMENT`<br>`SMALL_PARCEL` | `CUSTOM`<br>`BOX`<br>`LETTER` | Enum-validated against unauthorized arbitrary types. |
| **Priority** | Enum | Must be one of `STANDARD`, `EXPRESS`. | `STANDARD`<br>`EXPRESS` | `OVERNIGHT`<br>`URGENT` | Permitted service levels. |
| **Pickup Date** | Date | ISO Date. Server-side validation: `>= today` and `<= today + 14 days`. | `2026-09-07`<br>`2026-09-12` | `2020-01-01` (past)<br>`2028-01-01` | Guarantees collection cannot be scheduled in the past or indefinitely far in the future. |
| **Idempotency Key** | Token | Unique token (16 to 128 characters), typically UUIDv4. Unique index in database. | `c4b123d4-9f8a-4c28-98e3-0d5b4e78a631` | Empty string, whitespace | Prevents duplicate pickup rows on network retries or double form submissions. |
