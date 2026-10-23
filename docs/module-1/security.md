# Module 1: Security & Threat Mitigation Review

## 1. Authentication & Cryptography
- **Password Hashing**: Implemented using **Argon2id** (`argon2-cffi`). Passwords are never stored in plaintext, never echoed in API schemas, and never logged.
- **JWT Token Management**: Signed using HMAC-SHA256 (`HS256`) with a 32+ character secret key.
  - Claims: `sub` (user ID), `role` (`CITIZEN | AGENT | ADMIN`), `iat`, `exp`.
  - Tokens expire after 24 hours (`JWT_EXPIRATION_MINUTES = 1440`).

---

## 2. Role-Based Access Control (RBAC)
- **Public Registration Barrier**: `POST /auth/register` hardcodes `role = UserRole.CITIZEN`. Clients cannot pass `role: "ADMIN"` or `role: "AGENT"`.
- **Endpoint Protection**: Reusable FastAPI dependencies (`require_roles(...)`) enforce role authorization prior to executing route logic.
  - Citizens attempting to access `/api/v1/agent/*` receive `403 Forbidden`.
  - Delivery agents attempting to access citizen booking endpoints receive `403 Forbidden`.

---

## 3. IDOR & Ownership Verification
- **Parcels**: A citizen can only retrieve their own parcels (`sender_id == current_user.id`).
- **Pickups**: A citizen can only retrieve or cancel their own pickup request (`requester_id == current_user.id`).
- **Delivery Agents**: An agent can only access or modify pickups where `assigned_agent_id == agent.id`.
- **Privilege Stripping**: Creation schemas for parcels and pickups omit `sender_id`, `requester_id`, and `assigned_agent_id`. These fields are strictly derived from server-side JWT context.

---

## 4. State Machine Tamper Prevention
- Routes do not allow arbitrary status updates.
- All mutations pass through `transition_pickup_status(...)` in `app/services/state_machine.py`.
- Disallows invalid transitions (e.g. `PENDING -> PICKED_UP`, `PICKED_UP -> CANCELLED`).
- Verifies actor role and actor identity before granting transitions.

---

## 5. Concurrency & Idempotency
- **Idempotent Pickups**: Every pickup request requires an `Idempotency-Key` header. If a duplicate request is received, the backend immediately returns the existing pickup record without creating duplicate rows or re-assigning agents.
- **Tracking ID Sequence**: Generated via server-side PostgreSQL sequence (`postal_tracking_seq`) which is concurrency-safe and immune to client tampering.

---

## 6. Information Leakage Prevention
- Generic exception handler intercepts unexpected 500 errors and suppresses database credentials, SQL statements, and Python tracebacks.
- Structured application logging records events (e.g. `Parcel created: ID=X`) without logging passwords, tokens, or personal identifiers.
