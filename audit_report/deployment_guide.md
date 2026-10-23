# Smart Postal Management System — Deployment & Operations Guide

This guide documents the procedures for local development, production containerized deployment, database migration management, health checks, and troubleshooting.

---

## 1. System Architecture & Requirements

### Component Topology
- **Frontend:** React 18 SPA built with Vite 5. Serves citizen, postal agent, and administrator dashboards.
- **Backend:** FastAPI (Python 3.11/3.12) with asynchronous routing, Argon2id security, JWT authentication, and slowapi rate limiting.
- **Database:**
  - Production: PostgreSQL 15+ with Alembic migrations and native sequences (`postal_tracking_seq`).
  - Development / Testing: Canonical SQLite database (`backend/smart_postal.db`) with sequence emulation.
- **AI & Retrieval:**
  - Hybrid Lexical Full-Text Search (tsvector / ts_rank_cd cover-density ranking).
  - Dense Semantic Retrieval using local `sentence-transformers/all-MiniLM-L6-v2` embeddings (384-dimensional NumPy archive).
  - Grounded RAG with Groq or Google Gemini provider.

---

## 2. Local Development Execution

### A. Backend Setup
1. Open terminal in `backend/`:
   ```bash
   cd backend
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run database migrations:
   ```bash
   alembic upgrade head
   ```
3. Start the FastAPI development server:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   API interactive documentation will be accessible at: `http://127.0.0.1:8000/docs`

### B. Frontend Setup
1. Open terminal in `frontend/`:
   ```bash
   cd frontend
   npm install
   ```
2. Start the Vite dev server:
   ```bash
   npm run dev -- --host 127.0.0.1 --port 5173
   ```
   Web interface accessible at: `http://127.0.0.1:5173`

---

## 3. Containerized Deployment (Docker Compose)

The multi-container orchestration includes PostgreSQL, FastAPI backend, and Nginx frontend on an isolated bridge network (`postal_net`).

### Prerequisites
- Docker Engine 24.0+
- Docker Compose v2.20+

### A. Environment Configuration
Create `.env` in the repository root:
```ini
APPLICATION_ENV=production
DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/smart_postal_db
JWT_SECRET=YOUR_MINIMUM_32_CHAR_RANDOM_HIGH_ENTROPY_PRODUCTION_KEY
GROQ_API_KEY=YOUR_GROQ_API_KEY_HERE
```

### B. Launching Services
```bash
docker compose up -d --build
```

### C. Container Health Check Verification
Verify all containers report `healthy`:
```bash
docker compose ps
```
- PostgreSQL probe: `pg_isready -U postgres`
- Backend probe: `curl -f http://localhost:8000/api/v1/health`
- Frontend access: `http://localhost:80` (reverse proxies `/api/` to backend)

### D. Applying Database Migrations in Container
```bash
docker compose exec backend alembic upgrade head
```

### E. Shutdown
```bash
docker compose down
```
To preserve persistent volume data:
`docker compose down` retains `postgres_data`. To wipe volume data: `docker compose down -v`.

---

## 4. Operational Health Checks & Diagnostics

| Endpoint | Method | Purpose | Expected Response |
| :--- | :---: | :--- | :--- |
| `/api/v1/health` | `GET` | Service liveness & DB probe | `{"status": "UP", "database": "healthy"}` |
| `/api/v1/parcels/quote` | `POST` | Statutory pricing engine | Tariff quotation with itemized breakdown |
| `/api/v1/postal/retrieve` | `GET` | Document retrieval verification | Top matched postal statutory chunks |

---

## 5. Security & Rate Limiting Configurations

Rate limits are configured in `backend/app/config.py` and can be adjusted via environment variables:
- `RATE_LIMIT_LOGIN`: Maximum login attempts (default: `5/minute`)
- `RATE_LIMIT_REGISTER`: Maximum registration attempts (default: `5/minute`)
- `RATE_LIMIT_OTP`: Maximum OTP generation requests (default: `3/minute`)
- `RATE_LIMIT_RAG`: Maximum RAG questions (default: `10/minute`)
- `RATE_LIMIT_STORAGE_URL`: Storage backend (default: `memory://`, production: `redis://redis:6379/0`)

---

## 6. Troubleshooting Common Issues

1. **Production Startup Rejection (`Insecure JWT_SECRET`):**
   - *Cause:* Running with `APPLICATION_ENV=production` while `JWT_SECRET` is unset, under 32 characters, or using the default placeholder string.
   - *Fix:* Generate a secure random 32-byte key: `openssl rand -hex 32` and set `JWT_SECRET` in production environment.
2. **Missing Dense Vector Embeddings:**
   - *Cause:* `postal_chunk_embeddings.npz` missing or corrupt.
   - *Behavior:* System automatically falls back to cover-density lexical search (`hybrid_fallback`) and continues servicing queries.
   - *Fix:* Re-generate vector archive: `python scripts/data/generate_postal_embeddings.py --force`.
3. **Database Path Divergence:**
   - *Cause:* Running seed script from root previously created a separate SQLite file.
   - *Fix:* All scripts now use `settings.canonicalize_sqlite_path` pointing strictly to `backend/smart_postal.db`.
