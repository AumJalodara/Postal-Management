# Module 1: Testing & Verification Report

The test suite is built using **Pytest** and the **FastAPI TestClient** (httpx).

---

## 1. Test Suite Summary

Total Test Cases: **27 / 27 Passed (100%)**

```text
backend/tests/test_agent_assignment.py::test_agent_assignment_lowest_workload PASSED
backend/tests/test_agent_assignment.py::test_agent_assignment_tiebreaker_and_unavailable PASSED
backend/tests/test_agent_assignment.py::test_no_eligible_agent_remains_pending PASSED
backend/tests/test_auth.py::test_register_citizen_success PASSED
backend/tests/test_auth.py::test_register_duplicate_email PASSED
backend/tests/test_auth.py::test_register_ignores_client_role PASSED
backend/tests/test_auth.py::test_login_success_and_invalid_password PASSED
backend/tests/test_auth.py::test_auth_missing_or_invalid_token PASSED
backend/tests/test_idempotency.py::test_idempotent_pickup_creation PASSED
backend/tests/test_rbac.py::test_citizen_cannot_access_agent_endpoints PASSED
backend/tests/test_rbac.py::test_citizen_cannot_view_another_citizens_parcel PASSED
backend/tests/test_rbac.py::test_sender_id_derived_from_jwt_not_body PASSED
backend/tests/test_state_machine.py::test_pickup_full_lifecycle_and_history PASSED
backend/tests/test_state_machine.py::test_invalid_transitions PASSED
backend/tests/test_state_machine.py::test_cancellation_by_citizen PASSED
backend/tests/test_tracking_concurrency.py::test_concurrent_parcel_tracking_id_uniqueness PASSED
backend/tests/test_validation.py::test_name_valid PASSED
backend/tests/test_validation.py::test_name_invalid PASSED
backend/tests/test_validation.py::test_phone_valid PASSED
backend/tests/test_validation.py::test_phone_invalid PASSED
backend/tests/test_validation.py::test_pin_valid PASSED
backend/tests/test_validation.py::test_pin_invalid PASSED
backend/tests/test_validation.py::test_weight_valid PASSED
backend/tests/test_validation.py::test_weight_invalid PASSED
backend/tests/test_validation.py::test_address_valid PASSED
backend/tests/test_validation.py::test_address_invalid PASSED
backend/tests/test_validation.py::test_pickup_date PASSED
```

---

## 2. Key Test Scenarios

### 2.1 Concurrency & Uniqueness Test
- **File**: `backend/tests/test_tracking_concurrency.py`
- **Execution**: Dispatches 50 simultaneous parcel creation requests across a multi-threaded pool (`max_workers=10`).
- **Assertion**: Verifies that 50 requests succeed (HTTP 201) and produce exactly 50 unique tracking IDs matching format `GPM-2026-XXXXXX`.

### 2.2 Idempotency Test
- **File**: `backend/tests/test_idempotency.py`
- **Execution**: Submits the same pickup payload twice with the identical `Idempotency-Key` header.
- **Assertion**: First request creates Pickup #X. Second request returns the exact same Pickup #X without creating duplicate records or modifying database counts.

### 2.3 State Machine Transition Matrix Test
- **File**: `backend/tests/test_state_machine.py`
- **Execution**:
  - Tests allowed path: `PENDING -> ASSIGNED -> ACCEPTED -> PICKED_UP`.
  - Tests cancellation: `PENDING -> CANCELLED`, `ASSIGNED -> CANCELLED`.
  - Tests disallowed paths: `PENDING -> PICKED_UP` (fails), `PICKED_UP -> CANCELLED` (fails), `PICKED_UP -> PENDING` (fails).
  - Asserts audit history entries recorded for every transition.

### 2.4 Agent Assignment Workload Test
- **File**: `backend/tests/test_agent_assignment.py`
- **Execution**: Configures Agent 1 with workload 0 and Agent 2 with workload 1 for PIN 600001.
- **Assertion**: Agent 1 is selected due to lower workload. In subsequent test, marks Agent 1 unavailable; Agent 2 is correctly chosen. For unserviced PIN 500001, verifies pickup remains `PENDING`.

### 2.5 RBAC & Ownership Security Test
- **File**: `backend/tests/test_rbac.py`
- **Execution**: Citizen attempts to view another citizen's parcel or access `/api/v1/agent/pickups`.
- **Assertion**: Denied with `403 Forbidden` (`FORBIDDEN_ROLE` / `ACCESS_DENIED`). Client-supplied `sender_id: 999` is rejected/ignored and sender is forced to authenticated user ID.

---

## 3. Running Automated Tests

```bash
cd smart-postal-system
python -m pytest backend/tests -v
```
