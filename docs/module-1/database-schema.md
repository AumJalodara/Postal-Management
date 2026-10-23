# Module 1: Database Schema & Entity Relationships

## 1. Entity Relationship Overview

```text
  users (1) ────< (0..1) delivery_agents
    │  (1)
    ├─────< (0..*) parcels
    │  (1)
    ├─────< (0..*) pickup_requests
    │  (1)
    └─────< (0..*) pickup_status_history

  parcels (1) ────< (0..1) pickup_requests

  delivery_agents (1) ────< (0..*) pickup_requests (assigned_agent_id)

  pickup_requests (1) ────< (1..*) pickup_status_history
```

---

## 2. Table Definitions

### 2.1 `users`
Stores registered citizens, delivery personnel, and administrators.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY | Unique user identifier |
| `name` | VARCHAR(100) | NOT NULL | User's full name |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE, INDEX | Normalized lowercase email address |
| `phone` | VARCHAR(15) | NOT NULL | Canonical 10-digit mobile number |
| `password_hash` | VARCHAR(255) | NOT NULL | Argon2id cryptographic password hash |
| `role` | ENUM | NOT NULL, DEFAULT 'CITIZEN' | `CITIZEN`, `AGENT`, or `ADMIN` |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Account active flag |
| `created_at` | TIMESTAMPTZ | NOT NULL | Account creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Last update timestamp (UTC) |

### 2.2 `delivery_agents`
Stores delivery personnel operational parameters and current workload.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY | Delivery agent identifier |
| `user_id` | INTEGER | NOT NULL, UNIQUE, FK (`users.id` ON DELETE CASCADE) | Referenced user account (role=AGENT) |
| `service_area` | VARCHAR(50) | NOT NULL, INDEX | PIN code or service area zone |
| `is_available` | BOOLEAN | NOT NULL, DEFAULT TRUE, INDEX | Current duty / dispatch availability |
| `active_pickup_count`| INTEGER | NOT NULL, DEFAULT 0 | Real-time count of currently active pickups |
| `last_assigned_at` | TIMESTAMPTZ | NULLABLE | Timestamp of most recent pickup assignment |
| `created_at` | TIMESTAMPTZ | NOT NULL | Profile creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Last profile update |

### 2.3 `parcels`
Consignments booked by citizens.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY | Parcel identifier |
| `tracking_id` | VARCHAR(30) | NOT NULL, UNIQUE, INDEX | Prototype tracking ID (e.g. `GPM-2026-000001`) |
| `sender_id` | INTEGER | NOT NULL, FK (`users.id` ON DELETE CASCADE) | Authenticated citizen who booked the parcel |
| `receiver_name` | VARCHAR(100) | NOT NULL | Consignee's full name |
| `receiver_phone` | VARCHAR(15) | NOT NULL | Consignee's 10-digit mobile number |
| `destination_address`| VARCHAR(300)| NOT NULL | Delivery street address |
| `destination_city` | VARCHAR(100) | NOT NULL | Destination city/district |
| `destination_state`| VARCHAR(100) | NOT NULL | Destination state |
| `destination_pin` | VARCHAR(6) | NOT NULL, INDEX | Destination 6-digit Indian PIN |
| `weight` | NUMERIC(6, 2)| NOT NULL, CHECK (`weight > 0 AND weight <= 50`) | Consignment weight in kg |
| `parcel_type` | ENUM | NOT NULL | `DOCUMENT`, `SMALL_PARCEL`, `MEDIUM_PARCEL`, `LARGE_PARCEL` |
| `priority` | ENUM | NOT NULL, DEFAULT 'STANDARD' | `STANDARD`, `EXPRESS` |
| `created_at` | TIMESTAMPTZ | NOT NULL | Booking timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Update timestamp |

### 2.4 `pickup_requests`
Doorstep collection requests scheduled by citizens.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY | Unique pickup request ID |
| `parcel_id` | INTEGER | NOT NULL, UNIQUE, FK (`parcels.id` ON DELETE CASCADE) | One pickup request per consignment |
| `requester_id` | INTEGER | NOT NULL, FK (`users.id` ON DELETE CASCADE) | Citizen requesting the collection |
| `pickup_address` | VARCHAR(300)| NOT NULL | Collection address |
| `pickup_city` | VARCHAR(100) | NOT NULL | Collection city |
| `pickup_state` | VARCHAR(100) | NOT NULL | Collection state |
| `pickup_pin` | VARCHAR(6) | NOT NULL, INDEX | Collection 6-digit Indian PIN |
| `requested_date` | DATE | NOT NULL | Scheduled collection date |
| `assigned_agent_id`| INTEGER | NULLABLE, FK (`delivery_agents.id` ON DELETE SET NULL) | Assigned postal delivery agent |
| `status` | ENUM | NOT NULL, DEFAULT 'PENDING', INDEX | `PENDING`, `ASSIGNED`, `ACCEPTED`, `PICKED_UP`, `CANCELLED` |
| `idempotency_key` | VARCHAR(128)| NOT NULL, UNIQUE, INDEX | Client-supplied idempotent token |
| `created_at` | TIMESTAMPTZ | NOT NULL | Registration timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Last state transition timestamp |

### 2.5 `pickup_status_history`
Immutable audit log of all state machine transitions.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY | History entry ID |
| `pickup_id` | INTEGER | NOT NULL, FK (`pickup_requests.id` ON DELETE CASCADE) | Associated pickup |
| `old_status` | VARCHAR(50) | NULLABLE | Pre-transition status |
| `new_status` | VARCHAR(50) | NOT NULL | Post-transition status |
| `changed_by` | INTEGER | NULLABLE, FK (`users.id` ON DELETE SET NULL) | Actor user ID (NULL for SYSTEM) |
| `changed_by_role` | VARCHAR(50) | NOT NULL | `SYSTEM`, `CITIZEN`, `AGENT`, or `ADMIN` |
| `reason` | VARCHAR(255) | NULLABLE | Reason or remark for transition |
| `created_at` | TIMESTAMPTZ | NOT NULL | Timestamp when transition occurred |

---

## 3. PostgreSQL Sequence

- **Name**: `postal_tracking_seq`
- **Definition**: `CREATE SEQUENCE postal_tracking_seq START WITH 1 INCREMENT BY 1;`
- **Usage**: Server calls `nextval('postal_tracking_seq')` to obtain a strictly atomic sequence number for `GPM-2026-XXXXXX` tracking ID formatting.
