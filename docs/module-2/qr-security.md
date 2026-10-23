# Module 2 — QR Security & Privacy Architecture

---

## 1. Threat Model & Design Goals

1. **Anti-Enumeration**: Standard database integer identifiers (e.g., `parcel_id=1, 2, 3`) allow trivial scraping of national delivery volumes and recipient details.
2. **Data Leakage in Transit**: Printing cleartext phone numbers, full names, or addresses inside the 2D matrix allows anyone with a smartphone camera to harvest citizen Personally Identifiable Information (PII).
3. **Counterfeiting / Replay**: A QR code must resolve idempotently without leaking operational secrets.

---

## 2. Security Controls

### 2.1 Cryptographic Opaque Tokens
Each parcel is assigned an unguessable token generated with Python's `secrets.token_urlsafe(24)`:
```text
GPMQR-k3J9_aBCdEfGhIjKlMnOpQrStUvWxYz
```
* The QR matrix encodes solely the HTTPS resolution URL:  
  `https://postal-service.gov.in/track/qr/GPMQR-...`
* Direct database IDs, citizen passwords, or customer phone numbers are **never** present in the QR code payload.

### 2.2 Privacy Masking Engine
When `POST /api/v1/qr/resolve` or `GET /parcels/{id}/tracking` is invoked publicly:
* Citizen names are masked: `Rahul Kumar` -> `R**** K****`
* Complete residential street addresses are withheld; only the destination city and PIN code are exposed.
* Citizen phone numbers, email addresses, and agent internal IDs are entirely omitted from public JSON responses.

### 2.3 Token Revocation Support
The `parcel_qr_codes` table includes a `revoked_at` column. If a package is reprinted, replaced, or reported compromised, the token can be revoked immediately (`410 Gone: QR_REVOKED`).
