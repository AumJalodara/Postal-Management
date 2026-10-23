# Module 2 — REST API Specification

**Prefix**: `/api/v1`  
**Authentication**: Bearer JWT (Header: `Authorization: Bearer <token>`)

---

## 1. QR Code Management

### 1.1 `GET /api/v1/parcels/{tracking_id}/qr`
Retrieve or idempotently generate the opaque QR tracking code for a consignment.
* **Role Required**: `CITIZEN` (Sender), `AGENT`, or `ADMIN`.
* **Success Response (200 OK)**:
```json
{
  "success": true,
  "data": {
    "tracking_id": "GPM-2026-000001",
    "qr_token": "GPMQR-k3J9_aBC...",
    "qr_code_base64": "data:image/png;base64,iVBORw0KGgo...",
    "payload_url": "http://localhost:3000/track/qr/GPMQR-k3J9_aBC...",
    "created_at": "2026-09-09T17:30:00Z"
  }
}
```

### 1.2 `POST /api/v1/qr/resolve`
Public endpoint to resolve a scanned QR code token to a tracking record.
* **Role Required**: Public (Unauthenticated permitted).
* **Request Body**:
```json
{
  "qr_token": "GPMQR-k3J9_aBC..."
}
```
* **Success Response (200 OK)**:
```json
{
  "success": true,
  "data": {
    "tracking_id": "GPM-2026-000001",
    "current_status": "OUT_FOR_DELIVERY",
    "sender_masked": "R**** K****",
    "receiver_masked": "P**** S*****",
    "destination_city": "Chennai",
    "destination_pin": "600001",
    "last_updated": "2026-09-09T17:35:00Z",
    "timeline": [
      {
        "id": 1,
        "parcel_id": 1,
        "previous_status": null,
        "new_status": "BOOKED",
        "event_type": "BOOKED",
        "location_label": "Chennai (Booking Office)",
        "description": "Consignment booked successfully by citizen.",
        "actor_type": "CITIZEN",
        "created_at": "2026-09-09T17:30:00Z"
      }
    ]
  }
}
```

---

## 2. Tracking Timeline

### 2.1 `GET /api/v1/parcels/{tracking_id}/tracking`
Public or authenticated tracking timeline view.
* **Role Required**: Public.
* **Success Response (200 OK)**: Same format as `POST /qr/resolve`.

### 2.2 `GET /api/v1/parcels/{tracking_id}/events`
List of all tracking events in chronological order.
* **Role Required**: Public / Authenticated.
* **Success Response (200 OK)**: Array of `TrackingEventResponse`.

---

## 3. Agent Lifecycle Updates

### 3.1 `POST /api/v1/parcels/{tracking_id}/events`
Advances the status of a parcel along the state machine.
* **Role Required**: `AGENT` or `ADMIN`.
* **Request Body**:
```json
{
  "new_status": "IN_TRANSIT",
  "location_label": "Eastern Sorting Center",
  "description": "Dispatched to regional hub"
}
```
* **Disallowed**: Cannot transition to `DELIVERED` through this endpoint (returns 400 Bad Request `DELIVERY_NOT_ALLOWED`).

---

## 4. Delivery OTP & Verification

### 4.1 `POST /api/v1/parcels/{tracking_id}/delivery-otp`
Triggers generation of 6-digit delivery confirmation code.
* **Precondition**: Consignment status must be `OUT_FOR_DELIVERY`.
* **Role Required**: `AGENT`, `ADMIN`, or `CITIZEN` (Sender).
* **Success Response (200 OK)**:
```json
{
  "success": true,
  "data": {
    "tracking_id": "GPM-2026-000001",
    "expires_at": "2026-09-09T17:40:00Z",
    "message": "Delivery verification code generated. Valid for 5 minutes.",
    "test_otp": "569379"
  }
}
```
*(Note: `test_otp` is only populated in non-production environments for automated testing).*

### 4.2 `POST /api/v1/parcels/{tracking_id}/verify-delivery`
Submits recipient OTP to atomically complete delivery.
* **Precondition**: Consignment status must be `OUT_FOR_DELIVERY`.
* **Role Required**: `AGENT` or `ADMIN`.
* **Request Body**:
```json
{
  "otp": "569379"
}
```
* **Success Response (200 OK)**:
```json
{
  "success": true,
  "data": {
    "tracking_id": "GPM-2026-000001",
    "status": "DELIVERED",
    "delivered_at": "2026-09-09T17:38:22Z",
    "verified": true
  }
}
```
* **Failure Responses**:
  * 400 Bad Request (`OTP_INVALID`): Decrements attempts and returns remaining attempts.
  * 400 Bad Request (`OTP_ATTEMPT_LIMIT_EXCEEDED`): Triggered if 5 failed attempts occur.
  * 400 Bad Request (`OTP_EXPIRED`): Triggered if 5 minutes elapse.
  * 400 Bad Request (`PARCEL_ALREADY_DELIVERED`): Replay protection block.
