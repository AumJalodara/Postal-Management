# Module 1: Architecture & Engineering Decisions

This document records the key architectural and design decisions made for Module 1.

---

### 1. Why PostgreSQL
PostgreSQL provides enterprise-grade ACID transaction guarantees, concurrency safety, row-level locking (`FOR UPDATE`), native database sequences, check constraints, and enum support. This prevents data corruption during simultaneous bookings and doorstep assignments.

---

### 2. Why FastAPI
FastAPI offers high-performance asynchronous request handling, native integration with Pydantic v2 for compile-time and runtime type safety, and automatic OpenAPI documentation generation. Dependency injection simplifies authentication and session isolation.

---

### 3. Why Argon2id
Argon2id is the winner of the Password Hashing Competition (PHC) and is the current industry gold standard. It provides balanced defense against both GPU-based brute-force attacks (memory hardness) and side-channel timing attacks.

---

### 4. Why Public Registration Creates Only CITIZEN
Allowing an unauthenticated user to register as `AGENT` or `ADMIN` creates an immediate privilege escalation vulnerability. Delivery agents represent postal employees handling physical consignments; their provisioning must be managed administratively or via controlled seed environments.

---

### 5. Why Tracking IDs are Prototype Identifiers
This system is an academic research prototype. Tracking IDs follow the pattern `GPM-2026-XXXXXX` (where GPM stands for *Government Postal Management prototype*). It explicitly does not use or impersonate official India Post article numbering schemes (e.g. Speed Post tracking barcodes).

---

### 6. Why PostgreSQL Sequence is Used
Sequences are non-blocking, atomic database primitives. Unlike `MAX(id) + 1` or in-memory application counters, database sequences operate reliably across concurrent worker threads without table locks or duplicate key collisions. Gapless sequences are not required; uniqueness is guaranteed.

---

### 7. Why Idempotency is Required for Doorstep Pickups
Users on mobile connections frequently double-click buttons or experience network dropouts that cause automated retries. An `Idempotency-Key` header ensures that duplicate submissions resolve to the already-created pickup request rather than creating duplicate consignment bookings and multiple agent dispatches.

---

### 8. Why the State Machine is Centralized
Distributing state transitions across multiple API route handlers leads to inconsistencies, missed audit logging, and authorization bypasses. Centralizing transitions in `app/services/state_machine.py` ensures that all state mutations undergo identical transition rule validation, role checks, and atomic history recording.

---

### 9. Why QR, RAG, and GPS are Excluded from Module 1
Module 1 focuses strictly on foundational User, Consignment Booking, and Doorstep Pickup workflows. Prematurely integrating OCR, vector search (RAG), GPS tracking, and route optimization adds architectural coupling and unnecessary overhead before the core database models and state machine are validated.
