# Module 2 — Parcel Tracking State Machine

**Component**: `app.services.tracking_state_machine`  
**Authoritative Implementation**: `transition_parcel_tracking()`

---

## 1. State Matrix & Allowed Transitions

```text
[ BOOKED ]
    │
    ▼
[ PICKED_UP ]
    │
    ▼
[ IN_TRANSIT ]
    │
    ▼
[ ARRIVED_AT_HUB ]
    │
    ▼
[ OUT_FOR_DELIVERY ] ◄────────┐
    │          │              │
    │          ▼              │
    │   [ DELIVERY_ATTEMPTED ]┘
    │
    ▼ (REQUIRES VALID OTP)
[ DELIVERED ] (Terminal State)
```

### Transition Table

| Source Status | Target Status | Permitted Actor | Guard Condition |
|---|---|---|---|
| `BOOKED` | `PICKED_UP` | `AGENT`, `ADMIN`, `SYSTEM` | Doorstep collection completed |
| `PICKED_UP` | `IN_TRANSIT` | `AGENT`, `ADMIN` | Dispatched to transit hub |
| `IN_TRANSIT` | `ARRIVED_AT_HUB` | `AGENT`, `ADMIN` | Hub scan verification |
| `ARRIVED_AT_HUB` | `OUT_FOR_DELIVERY` | `AGENT`, `ADMIN` | Dispatched on delivery route |
| `OUT_FOR_DELIVERY` | `DELIVERY_ATTEMPTED` | `AGENT`, `ADMIN` | Door locked / recipient absent |
| `DELIVERY_ATTEMPTED` | `OUT_FOR_DELIVERY` | `AGENT`, `ADMIN` | Re-scheduled delivery run |
| `OUT_FOR_DELIVERY` | `DELIVERED` | `AGENT`, `ADMIN` | **`is_otp_verified == True` STRICT** |

---

## 2. Hard Security Boundaries

1. **Strict Forward Progression**: A parcel cannot skip intermediate stages (e.g. `BOOKED -> ARRIVED_AT_HUB` or `BOOKED -> OUT_FOR_DELIVERY` returns `400 INVALID_TRACKING_TRANSITION`).
2. **Delivery Guard**: Direct transition to `DELIVERED` through the regular event update endpoint is rejected unconditionally with `400 DELIVERY_NOT_ALLOWED`. The only code path that sets `is_otp_verified=True` is `process_secure_delivery()` inside `app/services/delivery_service.py`.
3. **Terminality**: Once a parcel reaches `DELIVERED`, no further transitions are permitted.
4. **Append-Only Auditing**: Every transition writes an immutable `ParcelTrackingEvent` with the actor role, user ID, location, and reason.
