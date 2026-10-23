# Module 1: API Specification

Base URL: `/api/v1`

All responses follow a consistent envelope:

#### Success Response
```json
{
  "success": true,
  "data": { ... }
}
```

#### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description.",
    "details": null
  }
}
```

---

## 1. Authentication Endpoints

### `POST /auth/register`
- **Role**: Public
- **Description**: Registers a new citizen account. Public registration forces `role = CITIZEN`.
- **Request Body**:
  ```json
  {
    "name": "Rahul Kumar",
    "email": "rahul.kumar@example.com",
    "phone": "9876543210",
    "password": "Password@123"
  }
  ```
- **Response**: `201 Created`

### `POST /auth/login`
- **Role**: Public
- **Description**: Verifies credentials and returns a signed JWT access token.
- **Request Body**:
  ```json
  {
    "email": "rahul.kumar@example.com",
    "password": "Password@123"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "success": true,
    "data": {
      "access_token": "eyJhbGciOiJIUzI1NiIs...",
      "token_type": "bearer",
      "user_id": 1,
      "name": "Rahul Kumar",
      "email": "rahul.kumar@example.com",
      "role": "CITIZEN"
    }
  }
  ```

### `GET /auth/me`
- **Role**: Authenticated
- **Description**: Returns profile details of the current user.

---

## 2. Parcel Endpoints

### `POST /parcels`
- **Role**: CITIZEN, ADMIN
- **Description**: Books a consignment. Generates a prototype tracking ID (`GPM-2026-XXXXXX`). Sender ID is derived from the JWT.
- **Request Body**:
  ```json
  {
    "receiver_name": "Priya Sharma",
    "receiver_phone": "9876543211",
    "destination_address": "12/4 Gandhi Street, Near Bus Stand",
    "destination_city": "Chennai",
    "destination_state": "Tamil Nadu",
    "destination_pin": "600001",
    "weight": 1.5,
    "parcel_type": "DOCUMENT",
    "priority": "STANDARD"
  }
  ```
- **Response**: `201 Created`

### `GET /parcels/my`
- **Role**: CITIZEN, ADMIN
- **Description**: Returns all parcels booked by the calling citizen.

### `GET /parcels/{tracking_id}`
- **Role**: Authenticated (Ownership verified: sender, assigned agent, or admin)
- **Description**: Retrieves single consignment details.

---

## 3. Pickup Endpoints

### `POST /pickups`
- **Role**: CITIZEN, ADMIN
- **Headers**: `Idempotency-Key: <uuid-or-token>` (Required)
- **Description**: Schedules doorstep collection for an existing booked parcel. Dispatches automatic agent assignment algorithm.
- **Request Body**:
  ```json
  {
    "parcel_id": 1,
    "pickup_address": "Door 4, North Street, Anna Nagar",
    "pickup_city": "Chennai",
    "pickup_state": "Tamil Nadu",
    "pickup_pin": "600001",
    "requested_date": "2026-09-07"
  }
  ```
- **Response**: `201 Created`

### `GET /pickups/my`
- **Role**: CITIZEN, ADMIN
- **Description**: Returns all pickups booked by the calling citizen.

### `GET /pickups/{pickup_id}`
- **Role**: Authenticated (Requester citizen, assigned agent, or admin)
- **Description**: Retrieves pickup details, parcel info, and full chronological status history.

### `POST /pickups/{pickup_id}/cancel`
- **Role**: CITIZEN, ADMIN
- **Description**: Cancels a pickup request in `PENDING` or `ASSIGNED` state.
- **Request Body**:
  ```json
  {
    "reason": "Cancelled by citizen request"
  }
  ```

---

## 4. Delivery Agent Endpoints

### `GET /agent/pickups`
- **Role**: AGENT
- **Description**: Lists all pickups currently assigned to the authenticated agent.

### `POST /agent/pickups/{pickup_id}/accept`
- **Role**: AGENT (Assigned agent only)
- **Description**: Transitions pickup from `ASSIGNED` to `ACCEPTED`.
- **Request Body**:
  ```json
  {
    "reason": "Pickup accepted by delivery agent"
  }
  ```

### `POST /agent/pickups/{pickup_id}/complete`
- **Role**: AGENT (Assigned agent only)
- **Description**: Transitions pickup from `ACCEPTED` to `PICKED_UP`. Automatically decrements the agent's active pickup workload.
- **Request Body**:
  ```json
  {
    "reason": "Consignment collected from doorstep"
  }
  ```

---

## 5. Health Probe

### `GET /health`
- **Role**: Public
- **Description**: Checks service availability and database connectivity.
