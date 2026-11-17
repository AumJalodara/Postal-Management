# Government Postal Management System
## *A Hybrid Information Retrieval and Retrieval-Augmented Generation Framework for Intelligent Postal Service Management*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.143.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB.svg?logo=react)](https://reactjs.org)
[![Vite](https://img.shields.io/badge/Vite-5.2.11-646CFF.svg?logo=vite)](https://vitejs.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg?logo=postgresql)](https://www.postgresql.org)
[![SentenceTransformers](https://img.shields.io/badge/Sentence--Transformers-all--MiniLM--L6--v2-FFA800.svg)](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
[![Tests](https://img.shields.io/badge/Tests-111%20Passed-brightgreen.svg)]()

> **Academic Prototype Notice**: This software is an academic engineering and research prototype developed for educational and experimental purposes. It is **NOT official India Post software** and does not interface with official India Post production systems or live government databases.

---

## 1. Executive Summary & Research Scope

Traditional government postal systems frequently struggle with legacy tracking opacity, delivery non-repudiation disputes, heuristic logistics inefficiencies, and inaccessible statutory regulations spread across hundreds of pages of legal gazettes (*The Post Office Act, 2023* and *The Post Office Rules, 2024*).

This project implements an enterprise-grade postal platform featuring **five core operational modules** coupled with an authoritative **Hybrid Information Retrieval (IR) and Grounded Retrieval-Augmented Generation (RAG)** framework. It seamlessly integrates daily postal logistics (booking, pickup dispatch, physical camera QR scanning, OTP-verified proof of delivery, and heuristic route optimization) with real-time statutory regulatory intelligence.

---

## 2. System Architecture

```text
+-----------------------------------------------------------------------------------+
|               Presentation Layer: React 18 + Vite SPA + Tailwind CSS              |
|   Citizen Portal  |  Agent Mobile Queue  |  Admin Dashboard  |  Postal AI Chat    |
+-----------------------------------------+-----------------------------------------+
                                          | REST API (Axios / Bearer JWT)
+-----------------------------------------v-----------------------------------------+
|                  Application Layer: FastAPI (Asynchronous ASGI)                   |
|  - Role-Based Access Control (CITIZEN, AGENT, STAFF, ADMIN)                       |
|  - Cryptographic Argon2id Password & OTP Hashing                                  |
|  - Stateful Token Revocation (RevokedToken table + jti nonces)                   |
|  - SlowAPI Sliding Window Rate Limiting                                           |
+-----------------------------------------+-----------------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                                                   |
+-------v-----------------------------------+   +---------------------------v-------+
|     Postal Operations & Logistics         |   |    Hybrid IR & Grounded RAG       |
| - Authoritative Tariff Engine             |   | - 228 Legal Statutory Chunks      |
| - Atomic Tracking ID (GPM-YYYY-XXXXXX)   |   | - PostgreSQL tsvector (GIN FTS)   |
| - Opaque QR Tokens (GPMQR-...)            |   | - MiniLM-L6-v2 Dense Embeddings   |
| - Argon2id Delivery OTP (Digital PoD)     |   | - Reciprocal Rank Fusion (k=60)   |
| - Haversine + Nearest Neighbor + 2-opt    |   | - Grounded RAG + Citation Checker |
+-------------------+-----------------------+   +-------------------+---------------+
                    |                                               |
+-------------------v-----------------------------------------------v---------------+
|                        Persistence & Evidence Layer                               |
| - PostgreSQL 15 / SQLite3 Relational Database (Parcels, Pickups, Tracking, Users) |
| - Offline Dense Vector Matrix (data/postal_documents/embeddings/ - 384 dimensions)|
| - Official Legal Gazette PDF Ingestion Pipeline (pypdf + Dynamic Hot-Indexing)   |
+-----------------------------------------------------------------------------------+
```

---

## 3. Implemented Modules Overview

### Module 1: User & Authentication Management
- **Role-Based Access Control (RBAC):** Strict authorization enforcing four distinct roles: `CITIZEN`, `AGENT`, `STAFF`, and `ADMIN`.
- **Cryptographic Security:** Argon2id password hashing; signed JWT access tokens carrying unique `jti` (JWT ID) claims.
- **Server-Side Token Revocation:** Instant session invalidation via a persistent `revoked_tokens` table on logout (`POST /api/v1/auth/logout`).
- **Profile Self-Service:** Profile inspection and updating via `GET/PUT /api/v1/auth/me`.

### Module 2: Parcel Booking & Doorstep Pickup
- **Authoritative Server-Side Tariffs:** Consignment pricing computed strictly on the backend (`pricing_service.py`) based on parcel type, weight, and priority. Client-side tampering is prevented.
- **Geographic PIN Validation:** Validates Indian PIN codes against an authoritative directory of 19,000+ postal locations (`postal_location_service.py`), preventing address state/city mismatches.
- **Doorstep Pickup Scheduling:** Citizens schedule doorstep parcel collections within structured service windows mapped to local agent service areas.

### Module 3: QR-Based Tracking & Parcel Lifecycle
- **Concurrency-Safe Tracking IDs:** Atomic sequence generation outputting standardized identifiers (`GPM-YYYY-XXXXXX`, e.g., `GPM-2026-000001`).
- **Opaque QR Codes:** Base64-encoded PNG QR codes embedding unguessable cryptographic tokens (`GPMQR-<token_urlsafe(24)>`), preventing URL enumeration attacks.
- **Privacy PII Masking:** Public scan endpoints automatically mask citizen names and sensitive details (e.g., `Rahul Sharma` $\rightarrow$ `R**** S****`).
- **Real Hardware Camera QR Scanner:** Integrates `html5-qrcode` in `QRScanner.jsx` to scan physical labels using device webcams or mobile cameras.
- **Strict State Machine:** Enforces legal linear milestone transitions: `BOOKED` $\rightarrow$ `PICKED_UP` $\rightarrow$ `IN_TRANSIT` $\rightarrow$ `OUT_FOR_DELIVERY` $\rightarrow$ `DELIVERED`. Illegal state skips are rejected with `HTTP 409 Conflict`.

### Module 4: Delivery & Logistics Management
- **Digital Proof of Delivery (PoD):** When a parcel reaches `OUT_FOR_DELIVERY`, a cryptographically random 6-digit OTP is generated. The plaintext is never persisted—only its Argon2id hash is stored. Delivery completion requires matching the OTP, enforcing a 15-minute expiration window and a 5-attempt rate limit.
- **Heuristic Route Optimization:** Solves the Traveling Salesperson Problem (TSP) for doorstep collections using:
  1. *Haversine Great-Circle Distance* between postal PIN centroids.
  2. *Greedy Nearest Neighbor* for initial tour construction.
  3. *2-opt Local Search* iterative edge-swapping for tour distance reduction.

### Module 5: Intelligent Search, Analytics & Administration
- **Operations Admin Portal:** Executive dashboard providing fleet telemetry, agent status, booking statistics, and delivery success metrics.
- **Dynamic Legal Document Ingestion:** Admin endpoint (`POST /api/v1/postal/upload`) allows uploading official PDF gazettes, extracting text, segmenting into statutory chunks, generating 384-dim dense embeddings on-the-fly, and dynamically updating the live index.
- **Hybrid Regulatory Retrieval:** Fuses lexical full-text search (`tsvector`, GIN, `ts_rank_cd`) and dense vector similarity via Reciprocal Rank Fusion (RRF, $k=60$) with statutory exact-target boosting.
- **Grounded Postal AI Assistant:** Generative RAG assistant (`PostalAssistant.jsx`) answering citizen and staff queries strictly based on retrieved statutory context, enforcing bracketed citations (`[1]`), validating citation provenance, and falling back to verified web search for non-statutory operational schemes (e.g., POPSK passport seva, Sukanya Samriddhi Yojana).

---

## 4. Intelligent Information Retrieval & Evaluation Benchmark

The retrieval engine was empirically benchmarked across **35 ground-truth statutory legal queries** using `scripts/data/evaluate_hybrid_retrieval.py`. Ground-truth evaluation results:

| Evaluation Metric | Lexical Search (`ts_rank_cd`) | Dense Semantic Search (`MiniLM-L6-v2`) | Hybrid Retrieval (RRF $k=60$) | Operational Gain |
| :--- | :---: | :---: | :---: | :--- |
| **Recall@1** | 85.71% | 77.14% | **85.71%** | Retains high top-rank precision |
| **Recall@3** | 91.43% | **94.29%** | 91.43% | Reliable multi-rank candidate capture |
| **Recall@5** | 91.43% | **97.14%** | 94.29% | Comprehensive statutory context |
| **Precision@5** | 0.2229 | **0.3257** | 0.2457 | High signal-to-noise ratio in legal chunks |
| **Mean Reciprocal Rank (MRR)** | 0.8857 | 0.9010 | **0.9303** | **Optimal ranking (relevant chunk at rank 1.07)** |
| **nDCG@5** | 0.8015 | **0.8489** | 0.8231 | Strong graded legal relevance |
| **Mean Latency** | **12.88 ms** | 24.75 ms | 42.36 ms | Sub-50ms real-time response time |

---

## 5. Technology Stack

| Layer | Technology | Version | Purpose in Project |
| :--- | :--- | :--- | :--- |
| **Frontend** | React, Vite, Tailwind CSS | React 18.3.1, Vite 5.2.11 | Modern, responsive Single-Page Application (SPA) |
| **Routing** | React Router DOM | 6.23.1 | Declarative client-side routing & auth route guards |
| **Barcode / QR** | HTML5-QRCode | 2.3.8 | Real hardware camera barcode/QR scanner integration |
| **HTTP Client** | Axios | 1.7.2 | Interceptor-based API client with JWT handling |
| **Backend** | FastAPI, Uvicorn, Starlette | FastAPI 0.143.0, Uvicorn 0.54.0 | Asynchronous high-performance REST API |
| **ORM / Migration** | SQLAlchemy, Alembic | SQLAlchemy 2.1.4, Alembic 1.20.0 | Type-safe ORM and versioned schema migrations |
| **Primary Database** | PostgreSQL 15 | `postgres:15-alpine` | Production relational database & GIN Inverted Index |
| **Dev / Test DB** | SQLite 3 | Embedded | Local development & rapid in-memory test runner |
| **Security & Auth** | PyJWT, Argon2-cffi | PyJWT 2.15.1, Argon2-cffi 25.1.0 | Cryptographic JWT tokens (`jti`) & Argon2id hashing |
| **Rate Limiting** | SlowAPI, Limits | SlowAPI 0.1.10, Limits 5.8.0 | Sliding window rate limiting on sensitive routes |
| **PDF Extraction** | pypdf, pytesseract | pypdf 6.19.0, pytesseract 0.3.13 | PDF parsing and OCR text extraction from gazettes |
| **Dense Embeddings** | SentenceTransformers | 6.1.0 (`all-MiniLM-L6-v2`) | Deterministic 384-dimensional dense semantic vectors |
| **LLM Inference** | Google Gemini / Groq | `google-genai`, `groq 1.7.0` | Grounded RAG text synthesis (`gemini-2.0-flash`) |
| **Testing** | pytest, pytest-asyncio | pytest 9.1.1, pytest-asyncio 1.4.0 | Automated backend test suite (**111 passing tests**) |

---

## 6. Repository Structure

```text
smart-postal-system/
├── frontend/                                # React + Vite Frontend Application
│   ├── src/
│   │   ├── components/                      # Reusable UI widgets, Navbar, ProtectedRoute
│   │   ├── pages/                           # 17 application pages across Citizen, Agent, Admin
│   │   │   ├── CreateParcel.jsx             # Server-priced booking form with geographic check
│   │   │   ├── CreatePickup.jsx             # Doorstep pickup scheduler
│   │   │   ├── TrackParcel.jsx              # Timeline tracking with PII privacy masking
│   │   │   ├── QRScanner.jsx                # Real hardware camera QR scanner
│   │   │   ├── DeliveryVerification.jsx     # Argon2id OTP verification & digital PoD
│   │   │   ├── AgentDeliveryQueue.jsx       # Delivery agent assigned delivery tasks
│   │   │   ├── OperationsDashboard.jsx      # Admin operations, PDF ingestion & live telemetry
│   │   │   └── PostalAssistant.jsx          # Grounded RAG chatbot with statutory citations
│   │   ├── services/                        # Axios API client modules
│   │   └── App.jsx                          # Route declarations & role boundaries
│   ├── package.json                         # Frontend dependencies & scripts
│   └── vite.config.js                       # Vite build configuration (Port 3000)
├── backend/                                 # FastAPI Python Backend Application
│   ├── app/
│   │   ├── models/                          # SQLAlchemy database entities (User, Parcel, etc.)
│   │   ├── schemas/                         # Pydantic data schemas & validation rules
│   │   ├── routes/                          # REST API routers (auth, parcels, tracking, postal, ops)
│   │   ├── services/                        # Business logic, pricing, OTP, route optimization, RAG
│   │   ├── auth/                            # Security, password hashing, JWT, RBAC dependencies
│   │   └── config.py                        # Centralized application settings & env loader
│   ├── tests/                               # 111 automated test cases (100% pass rate)
│   └── alembic/                             # Relational database schema migrations
├── data/                                    # Datasets, legal chunks, and embeddings
│   └── postal_documents/
│       ├── raw/                             # Official PDF gazettes (Act 2023, Rules 2024)
│       ├── chunks/                          # 228 structure-aware legal chunks (.jsonl)
│       ├── embeddings/                      # 384-dim vector matrix (.npz) & metadata (.json)
│       └── evaluation/                      # 35 benchmark queries & evaluation result records
├── scripts/
│   └── data/                                # Ingestion, chunking, embedding & evaluation scripts
├── docker-compose.yml                       # Multi-container orchestration (PostgreSQL 15)
├── .env.example                             # Environment variable template
└── README.md                                # Project documentation
```

---

## 7. Prerequisites & Installation

### Prerequisites
- **Python**: 3.10 to 3.14
- **Node.js**: 18+ (tested on Node v20/v24)
- **Database**: PostgreSQL 15+ (Production) or SQLite 3 (Default local dev)

### Backend Setup
1. Open a terminal and navigate to the project backend:
   ```bash
   cd smart-postal-system
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv backend/venv
   .\backend\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv backend/venv
   source backend/venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Copy the environment configuration:
   ```bash
   cp .env.example .env
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   npm install
   ```

---

## 8. Running the Application

### Option A: Standard Two-Terminal Execution

#### Terminal 1 — Start FastAPI Backend:
```powershell
backend\venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
- **Backend API:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **Health Check Endpoint:** `http://127.0.0.1:8000/health`

#### Terminal 2 — Start React / Vite Frontend:
```powershell
npm --prefix frontend run dev
```
- **Frontend Web Portal:** `http://localhost:3000`

---

## 9. Demo Credentials

The database contains pre-configured test accounts across all system roles:

| Role | Email | Password | Service PIN | Primary Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **Citizen** | `citizen.demo@example.com` | `Citizen@12345` | N/A | Book parcels, schedule pickups, track consignments |
| **Delivery Agent** | `agent.chennai@postal.gov.in` | `Agent@12345` | `600001` | Delivery queue, 2-opt route optimization, OTP verification |
| **Postal Staff** | `staff@postal.gov.in` | `Staff@12345` | `110001` | Counter parcel processing, internal tracking queries |
| **Administrator** | `admin@postal.gov.in` | `Admin@12345` | N/A | Operations dashboard, PDF legal document ingestion, analytics |

---

## 10. Automated Testing & Verification

Run the full automated test suite using `pytest`:

```powershell
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

### Verified Test Suite Breakdown (111 Tests, 100% Passing)
- `test_auth.py` & `test_jwt_config_hardening.py`: Argon2id hashing, JWT validation, server-side token revocation (`jti`).
- `test_rbac.py`: Role boundary enforcement across `CITIZEN`, `AGENT`, `STAFF`, and `ADMIN`.
- `test_parcel_pricing_security.py`: Server-side tariff calculations, weight tier validation, client tampering rejection.
- `test_validation.py` & `test_postal_location.py`: PIN code format validation and Indian directory state-consistency checks.
- `test_module2_qr.py` & `test_module2_tracking.py`: Opaque QR token generation, PII masking, and linear lifecycle states.
- `test_module2_otp.py` & `test_module2_delivery.py`: 6-digit OTP generation, Argon2id hashing, 5-attempt rate limiting, and Digital PoD.
- `test_route_optimization.py` & `test_eta_estimation.py`: Haversine distance, Nearest Neighbor, and 2-opt tour improvement.
- `test_postal_upload.py`: Admin PDF upload, statutory chunking, and dynamic vector indexing.
- `test_dense_fallback.py` & `test_web_enhanced_rag.py`: Graceful degradation to lexical search and web search fallback for external schemes.

---

## 11. License & Academic Attribution

This project is released under the **MIT License**.

When citing this work for academic research or publications, please cite:
```bibtex
@misc{smart_postal_system_2026,
  title={A Hybrid Information Retrieval and Retrieval-Augmented Generation Framework for Intelligent Postal Service Management},
  author={Smart Postal Research Group},
  year={2026},
  howpublished={\url{https://github.com/AumJalodara/Postal-Management}}
}
```



