# Module 2 — Delivery OTP Security Architecture

---

## 1. Cryptographic Generation & Storage

1. **Generation**:
   ```python
   raw_otp = str(secrets.randbelow(900000) + 100000)
   ```
   Uses cryptographically secure pseudorandom number generation (`secrets`), producing a uniform 6-digit numeric integer in the range `[100000, 999999]`.
2. **Argon2id Hashing**:
   Plaintext OTPs are **never persisted** to the database or written to operational logs. The code is hashed using Argon2id (matching user authentication passwords).
3. **Validity Window**:
   Expires in exactly 5 minutes (`expires_at = NOW() + 5 minutes`). Any verification attempt past this timestamp is rejected with `400 OTP_EXPIRED`.

---

## 2. Brute-Force & Race Condition Defenses

1. **Attempt Limits**:
   Each OTP record tracks failed attempts (`attempts INTEGER DEFAULT 0`). Submitting an incorrect OTP increments this counter and decrements the user's remaining attempts. Once `attempts >= 5`, the OTP is permanently locked (`400 OTP_ATTEMPT_LIMIT_EXCEEDED`).
2. **Replay Protection**:
   Upon valid verification, `verified_at = NOW()` is written immediately within the same transaction that transitions the parcel to `DELIVERED`. Re-submitting the same OTP is rejected (`400 OTP_ALREADY_USED` or `PARCEL_ALREADY_DELIVERED`).
3. **Concurrency & Row Locking**:
   In PostgreSQL, verification queries utilize `with_for_update()` to ensure thread-safe atomic evaluation under concurrent verification requests.
