from datetime import date
from tests.conftest import auth_header_for_user


def test_idempotent_pickup_creation(client, seed_users, db):
    c1 = seed_users["citizen1"]
    headers = auth_header_for_user(c1)

    # 1. Create a parcel
    p_resp = client.post("/api/v1/parcels", json={
        "receiver_name": "Suresh Raina",
        "receiver_phone": "9876543210",
        "destination_address": "Flat 3A, Marina Breeze Apartments",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 2.0,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=headers)
    parcel_id = p_resp.json()["data"]["id"]

    idempotency_key = "client-unique-uuid-987654"

    pickup_payload = {
        "parcel_id": parcel_id,
        "pickup_address": "Door 15, Beach Road, Santhome",
        "pickup_city": "Chennai",
        "pickup_state": "Tamil Nadu",
        "pickup_pin": "600001",
        "requested_date": str(date.today())
    }

    # Request 1
    r1 = client.post(
        "/api/v1/pickups",
        json=pickup_payload,
        headers={**headers, "Idempotency-Key": idempotency_key}
    )
    assert r1.status_code == 201
    pickup1 = r1.json()["data"]

    # Request 2 with exact same Idempotency-Key
    r2 = client.post(
        "/api/v1/pickups",
        json=pickup_payload,
        headers={**headers, "Idempotency-Key": idempotency_key}
    )
    assert r2.status_code == 201
    pickup2 = r2.json()["data"]

    # Verify both responses reference the same pickup record
    assert pickup1["id"] == pickup2["id"]
    assert pickup1["idempotency_key"] == pickup2["idempotency_key"]

    # Verify in database: exactly 1 pickup exists for this parcel
    from app.models.pickup import PickupRequest
    total_pickups = db.query(PickupRequest).filter(PickupRequest.parcel_id == parcel_id).count()
    assert total_pickups == 1


def test_pickup_rebooking_after_cancellation(client, seed_users, db):
    """
    Regression Test for ISSUE-10:
    When a pickup request is cancelled, the citizen can re-book a new pickup
    for the same parcel without hitting a database unique constraint failure.
    Concurrent active pickups remain prevented with 409 Conflict.
    """
    c1 = seed_users["citizen1"]
    headers = auth_header_for_user(c1)

    # 1. Book parcel
    p_resp = client.post("/api/v1/parcels", json={
        "receiver_name": "Deepak Chahar",
        "receiver_phone": "9876543210",
        "destination_address": "Flat 7B, Anna Nagar West",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 1.5,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=headers)
    assert p_resp.status_code == 201
    parcel_data = p_resp.json()["data"]
    parcel_id = parcel_data["id"]

    # Verify parcel response contains status
    assert parcel_data["status"] == "BOOKED"

    pickup_payload = {
        "parcel_id": parcel_id,
        "pickup_address": "Door 15, Beach Road, Santhome",
        "pickup_city": "Chennai",
        "pickup_state": "Tamil Nadu",
        "pickup_pin": "600001",
        "requested_date": str(date.today())
    }

    # 2. Create first pickup
    r1 = client.post(
        "/api/v1/pickups",
        json=pickup_payload,
        headers={**headers, "Idempotency-Key": "key-initial-pickup-1"}
    )
    assert r1.status_code == 201
    pickup1_id = r1.json()["data"]["id"]

    # 3. Cancel first pickup
    cancel_res = client.post(
        f"/api/v1/pickups/{pickup1_id}/cancel",
        json={"reason": "Need to change pickup time"},
        headers=headers
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "CANCELLED"

    # 4. Re-book pickup for the same parcel with a new idempotency key
    r2 = client.post(
        "/api/v1/pickups",
        json=pickup_payload,
        headers={**headers, "Idempotency-Key": "key-rebooked-pickup-2"}
    )
    assert r2.status_code == 201
    pickup2_id = r2.json()["data"]["id"]
    assert pickup2_id != pickup1_id

    # 5. Attempting to book a third pickup while pickup 2 is active must be rejected with 409 Conflict
    r3 = client.post(
        "/api/v1/pickups",
        json=pickup_payload,
        headers={**headers, "Idempotency-Key": "key-attempt-duplicate-3"}
    )
    assert r3.status_code == 409
    assert r3.json()["error"]["code"] == "ACTIVE_PICKUP_EXISTS"

