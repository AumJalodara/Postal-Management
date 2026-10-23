# Module 2 — Database Schema & Data Models

**Project**: AI-Powered Intelligent Government Postal Management and Information Retrieval System  
**Module**: Module 2 — QR-Based Parcel Tracking & Secure Delivery  

---

## 1. Schema Extensions & New Tables

Module 2 introduces four key tables and updates the existing `parcels` table.

### 1.1 Altered Table: `parcels`

Added `status` tracking column:
* `status VARCHAR(30) NOT NULL DEFAULT 'BOOKED'`  
  Constrained by `ParcelTrackingStatus` enum values (`BOOKED`, `PICKED_UP`, `IN_TRANSIT`, `ARRIVED_AT_HUB`, `OUT_FOR_DELIVERY`, `DELIVERY_ATTEMPTED`, `DELIVERED`).
* Added index `ix_parcels_status` for fast query performance in agent delivery queues.

---

### 1.2 Table: `parcel_tracking_events`

Maintains an append-only, immutable audit trail of all consignment state transitions.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY | Unique event sequence identifier |
| `parcel_id` | INTEGER | FOREIGN KEY (`parcels.id`), NOT NULL | Target parcel reference |
| `previous_status` | VARCHAR(30) | NULLABLE | Preceding status |
| `new_status` | VARCHAR(30) | NOT NULL | Status after transition |
| `event_type` | VARCHAR(50) | NOT NULL | Transition classification |
| `location_label` | VARCHAR(150) | NOT NULL | Facility or PIN code location |
| `description` | TEXT | NOT NULL | Detailed operational explanation |
| `actor_type` | VARCHAR(20) | NOT NULL | `SYSTEM`, `CITIZEN`, `AGENT`, `ADMIN` |
| `actor_id` | INTEGER | FOREIGN KEY (`users.id`), NULLABLE | User who performed the transition |
| `created_at` | DATETIME | NOT NULL, DEFAULT `NOW()` | Event timestamp |

**Indexes**:
* `ix_parcel_tracking_events_parcel_id`
* `ix_parcel_tracking_events_created_at`

---

### 1.3 Table: `parcel_qr_codes`

Stores opaque QR resolution tokens detached from internal auto-increment primary keys.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY | Unique QR record ID |
| `parcel_id` | INTEGER | FOREIGN KEY (`parcels.id`), NOT NULL | Associated parcel |
| `qr_token` | VARCHAR(128) | UNIQUE, NOT NULL | Opaque cryptographic token (`GPMQR-*`) |
| `created_at` | DATETIME | NOT NULL, DEFAULT `NOW()` | Generation timestamp |
| `revoked_at` | DATETIME | NULLABLE | Revocation timestamp if invalidated |

**Indexes**:
* `ix_parcel_qr_codes_qr_token` (Unique)
* `ix_parcel_qr_codes_parcel_id`

---

### 1.4 Table: `delivery_otps`

Maintains Argon2id-hashed delivery confirmation one-time passwords.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY | OTP record identifier |
| `parcel_id` | INTEGER | FOREIGN KEY (`parcels.id`), NOT NULL | Associated parcel |
| `otp_hash` | VARCHAR(255) | NOT NULL | Argon2id salted password hash |
| `expires_at` | DATETIME | NOT NULL | Absolute expiry (5 minutes from issue) |
| `attempts` | INTEGER | NOT NULL, DEFAULT 0 | Failed attempt counter |
| `max_attempts` | INTEGER | NOT NULL, DEFAULT 5 | Maximum allowed failed attempts |
| `created_at` | DATETIME | NOT NULL, DEFAULT `NOW()` | Generation timestamp |
| `verified_at` | DATETIME | NULLABLE | Timestamp when successfully consumed |

**Indexes**:
* `ix_delivery_otps_parcel_id`
* `ix_delivery_otps_created_at`

---

### 1.5 Table: `postal_locations` (Reference Foundation)

Future directory schema prepared for All India Pincode Directory integration.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY | Location ID |
| `pincode` | VARCHAR(6) | NOT NULL, INDEX | 6-digit Indian PIN code |
| `office_name` | VARCHAR(150) | NOT NULL | Post office name |
| `district` | VARCHAR(100) | NOT NULL | District name |
| `state` | VARCHAR(100) | NOT NULL | State name |
| `latitude` | NUMERIC(9, 6) | NULLABLE | Geographic latitude |
| `longitude` | NUMERIC(9, 6) | NULLABLE | Geographic longitude |
| `created_at` | DATETIME | NOT NULL | Timestamp |

---

## 2. Alembic Migration

Migration file: `backend/alembic/versions/002_module2_tracking_qr_otp.py`
Revision ID: `002_module2_tracking_qr_otp`
Down Revision: `001_initial_module1`

Supports both SQLite (WAL mode) and PostgreSQL engines with transactional DDL guards.
