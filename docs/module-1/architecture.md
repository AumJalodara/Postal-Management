# Module 1: Architecture Documentation

## Academic Prototype Context
This system is an **academic prototype** titled **AI-Powered Intelligent Government Postal Management and Information Retrieval System**. It is **NOT official India Post software** and has no access to confidential India Post operational, employee, GPS, or database information.

---

## 1. High-Level System Architecture

Module 1 (*User, Parcel Booking & Doorstep Pickup Management*) establishes the foundational vertical slice of the platform. It implements a strict 5-layer architecture:

```text
┌────────────────────────────────────────────────────────┐
│                   React + Vite SPA                     │
│  (Citizen Dashboard, Agent Workspace, Forms, Badges)   │
└───────────────────────────┬────────────────────────────┘
                            │ REST / JSON (Axios)
┌───────────────────────────▼────────────────────────────┐
│                    FastAPI Routers                     │
│    (/auth, /parcels, /pickups, /agent, /health)        │
└─────────────┬────────────────────────────┬─────────────┘
              │ Request / Response DTOs    │ Security Context
┌─────────────▼─────────────┐   ┌──────────▼─────────────┐
│    Pydantic v2 Schemas    │   │  Auth & RBAC Middleware│
│ (Type validation, filters)│   │(Argon2id, JWT, Roles)  │
└─────────────┬─────────────┘   └──────────┬─────────────┘
              │                            │
┌─────────────▼────────────────────────────▼─────────────┐
│                   Domain Services                      │
│ ┌──────────────────────┐  ┌──────────────────────────┐ │
│ │    ParcelService     │  │      PickupService       │ │
│ │ (Sequence Tracking ID│  │(Idempotency, Ownership)  │ │
│ └──────────────────────┘  └──────────────────────────┘ │
│ ┌──────────────────────┐  ┌──────────────────────────┐ │
│ │  AgentAssignService  │  │   PickupStateMachine     │ │
│ │ (Workload, Service)  │  │(Atomic state & history)  │ │
│ └──────────────────────┘  └──────────────────────────┘ │
└───────────────────────────┬────────────────────────────┘
                            │ SQLAlchemy 2.0 ORM
┌───────────────────────────▼────────────────────────────┐
│        PostgreSQL Database & Alembic Migrations        │
│  (users, delivery_agents, parcels, pickup_requests,    │
│   pickup_status_history, postal_tracking_seq)          │
└────────────────────────────────────────────────────────┘
```

---

## 2. Layer Responsibilities

### 2.1 Presentation Layer (Frontend)
- **Framework**: React 18 with Vite and React Router v6.
- **Role**: Renders an accessible, trustworthy government postal interface.
- **Validation**: Performs instant client-side feedback for names, Indian mobile numbers, PIN codes, weights, and pickup dates.
- **Idempotency**: Generates client-side UUID tokens attached in the `Idempotency-Key` header on pickup requests to prevent duplicate submissions.

### 2.2 Routing & API Layer (FastAPI)
- **Endpoints**: `/api/v1/auth`, `/api/v1/parcels`, `/api/v1/pickups`, `/api/v1/agent`, `/api/v1/health`.
- **Policy**: Routes remain thin adapters. They parse requests, invoke dependency injection (`get_current_user`, `get_db`), delegate business operations to domain services, and return standardized JSON envelopes.

### 2.3 Schemas & Validation Layer (Pydantic v2)
- **Role**: Authoritative contract enforcement and sanitization.
- **Security**: Strips client-injected privileged fields (e.g. clients cannot send `sender_id`, `role`, or `assigned_agent_id`).
- **Validators**: Enforces exact data type and domain rules (e.g. Indian mobile `^[6-9]\d{9}$`, PIN `^[1-9][0-9]{5}$`, weight `> 0 and <= 50 kg`).

### 2.4 Domain Services Layer
- **`TrackingService`**: Produces unique, concurrency-safe prototype tracking IDs formatted as `GPM-2026-XXXXXX` backed by PostgreSQL sequences.
- **`ParcelService`**: Manages consignment creation and strict ownership checks.
- **`AgentAssignmentService`**: Deterministic workload and PIN matching algorithm with tie-breaking rules.
- **`PickupStateMachine`**: Centralized state transition validator guaranteeing that only allowed status transitions and authorized actors can mutate state.
- **`PickupService`**: Orchestrates doorstep requests, enforces idempotency, prevents duplicate pickups on the same parcel, and dispatches agent assignment.

### 2.5 Persistence Layer (PostgreSQL & SQLAlchemy 2.0)
- **Engine**: PostgreSQL with ACID transactions.
- **Migrations**: Alembic (`alembic/versions/001_initial_module1.py`).
- **Constraints**: Enforces foreign keys with cascade policies, unique indexes on email, tracking ID, and idempotency key, plus check constraints on parcel weight.
