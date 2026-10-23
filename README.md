# AI-Powered Intelligent Government Postal Management and Information Retrieval System

> **Academic Prototype Notice**: This software is an academic research prototype. It is **NOT official India Post software** and does not have access to official India Post operational, employee, customer, GPS, or database systems.

---

## 1. Project Overview & Scope

This project implements a comprehensive smart postal management prototype, encompassing 4 complete modules.

### Modules Implemented

**Module 1 — Registration / Parcel / Pickup**
- Citizen registration & authentication (Argon2id password hashing, JWT bearer tokens).
- Consignment booking with multi-layer semantic validation.
- Concurrency-safe prototype tracking ID generation (`GPM-2026-XXXXXX`).
- Idempotent doorstep pickup scheduling.
- Centralized pickup lifecycle state machine.
- Role-based access control (CITIZEN, AGENT, ADMIN).

**Module 2 — QR / Tracking / OTP**
- QR tracking and scanner interface.
- Secure delivery OTP generation and verification.
- Tracking ledger and delivery lifecycle management.

**Module 3 — Postal IR + RAG**
- Official Postal Documents OCR and chunking.
- Hybrid Information Retrieval (Dense + Sparse with Reciprocal Rank Fusion).
- Grounded RAG (Retrieval-Augmented Generation) using LLMs to answer postal-regulation queries based strictly on retrieved official context.

**Module 4 — Assignment / Route / ETA / Operations**
- Intelligent Agent Assignment (distance + workload weighting).
- Route Optimization (Haversine + 2-opt).
- ETA Estimation.
- Operational History (append-only audit log).
- Operations API and Dashboard (Admin-only).
- AI Operations Assistant (Grounded Groq LLM queries for operational analytics).
- *(Note: Step 7 Location-Aware Delivery Verification is currently ON HOLD)*

---

## 2. Project Structure

```text
smart-postal-system/
├── frontend/                     # React + Vite Single Page Application
│   ├── src/
│   │   ├── components/           # UI components (Navbar, Navigation)
│   │   ├── pages/                # Citizen, Agent, and Admin dashboards, RAG assistant, QR tools
│   │   ├── services/             # Axios API client
│   │   └── App.jsx               # Application routing
├── backend/                      # FastAPI Python Application
│   ├── app/
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic validation schemas
│   │   ├── routes/               # API endpoints
│   │   ├── services/             # Business logic (Routing, ETA, LLM Providers, etc.)
│   │   ├── auth/                 # RBAC and security
│   │   └── config.py             # Configuration and environment variables
│   ├── tests/                    # Comprehensive Pytest test suite (250+ tests)
│   └── alembic/                  # Database migrations
├── data/                         # Synthetic data and Postal regulation PDFs
├── .env.example
└── README.md
```

---

## 3. Prerequisites

- **Python**: 3.10+ (tested on Python 3.14)
- **Node.js**: 18+ (tested on Node v24)
- **Database**: PostgreSQL 14+ (or Docker)

---

## 4. Environment Variables

Copy `.env.example` to `.env` in the `smart-postal-system/backend` directory:

```bash
cp .env.example .env
```

Default settings:
```ini
APPLICATION_ENV=development
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/smart_postal_db
JWT_SECRET=super-secret-dev-key-change-in-production-min32chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440
HOST=0.0.0.0
PORT=8000

# LLM Provider Configuration
LLM_PROVIDER=groq
# GROQ_API_KEY=gsk_your_real_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

> **Security Note:** Never commit your real `.env` file containing the `GROQ_API_KEY`. It should strictly remain out of version control.

---

## 5. Running the Application

### 5.1 Database Setup

Run Alembic migrations to set up the database schema:
```bash
cd smart-postal-system/backend
alembic upgrade head
```

Seed synthetic data:
```bash
cd smart-postal-system
python data/synthetic/seed_data.py
```

### 5.2 Start the Backend
```bash
cd smart-postal-system/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5.3 Start the Frontend
```bash
cd smart-postal-system/frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 6. Demo Accounts

| Role | Email | Password | Service Area PIN | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Citizen** | `citizen.demo@example.com` | `Citizen@12345` | N/A | Books parcels & requests pickups |
| **Agent** | `agent.chennai@postal.gov.in` | `Agent@12345` | `600001` | Delivery agent |
| **Admin** | `admin@postal.gov.in` | `Admin@12345` | N/A | System administration |

---

## 7. Testing

Run the complete Pytest test suite from the backend directory:
```bash
cd smart-postal-system/backend
python -m pytest tests/ ../tests/ -v
```

The comprehensive test suite (250+ tests) validates Module 1-4 capabilities, ensuring zero regressions on core components, concurrency protections, routing optimization accuracy, operations APIs, and RBAC implementation.
