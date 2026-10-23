import pytest
from datetime import date
from app.models.enums import PickupStatus, UserRole
from app.models.pickup import PickupRequest
from app.services.state_machine import transition_pickup_status
from tests.conftest import auth_header_for_user


def test_pickup_full_lifecycle_and_history(client, seed_users, db):
    c1 = seed_users["citizen1"]
    ag1 = seed_users["agent1"]
    ag1_user = seed_users["agent1_user"]
    headers_c1 = auth_header_for_user(c1)
    headers_ag1 = auth_header_for_user(ag1_user)

    # 1. Book Parcel
    p_resp = client.post("/api/v1/parcels", json={
        "receiver_name": "Kavita Rao",
        "receiver_phone": "9876543210",
        "destination_address": "Flat 102, Green Valley Apartments",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 1.5,
        "parcel_type": "DOCUMENT",
        "priority": "EXPRESS"
    }, headers=headers_c1)
    assert p_resp.status_code == 201
    parcel_id = p_resp.json()["data"]["id"]

    # 2. Request Pickup (PIN 600001 -> Agent 1 matches, workload 0 vs Agent 2 workload 1)
    pickup_resp = client.post("/api/v1/pickups", json={
        "parcel_id": parcel_id,
        "pickup_address": "Door 4, North Street, Anna Nagar",
        "pickup_city": "Chennai",
        "pickup_state": "Tamil Nadu",
        "pickup_pin": "600001",
        "requested_date": str(date.today())
    }, headers={**headers_c1, "Idempotency-Key": "test-key-lifecycle-1"})
    assert pickup_resp.status_code == 201
    pickup_data = pickup_resp.json()["data"]
    pickup_id = pickup_data["id"]

    # Verify initial auto-assignment to Agent 1
    assert pickup_data["status"] == "ASSIGNED"
    assert pickup_data["assigned_agent_id"] == ag1.id

    # 3. Agent 1 Accepts Pickup (ASSIGNED -> ACCEPTED)
    accept_resp = client.post(f"/api/v1/agent/pickups/{pickup_id}/accept", headers=headers_ag1)
    assert accept_resp.status_code == 200
    assert accept_resp.json()["data"]["status"] == "ACCEPTED"

    # 4. Agent 1 Marks Pickup as PICKED_UP (ACCEPTED -> PICKED_UP)
    complete_resp = client.post(f"/api/v1/agent/pickups/{pickup_id}/complete", headers=headers_ag1)
    assert complete_resp.status_code == 200
    final_data = complete_resp.json()["data"]
    assert final_data["status"] == "PICKED_UP"

    # Verify History Entries
    history = final_data["history"]
    assert len(history) >= 3
    # Check statuses recorded
    statuses = [h["new_status"] for h in history]
    assert "PENDING" in statuses
    assert "ASSIGNED" in statuses
    assert "ACCEPTED" in statuses
    assert "PICKED_UP" in statuses


def test_invalid_transitions(client, seed_users, db):
    c1 = seed_users["citizen1"]
    ag1_user = seed_users["agent1_user"]

    # Create raw pickup in PENDING state
    pickup = PickupRequest(
        parcel_id=999,  # dummy for direct state machine test
        requester_id=c1.id,
        pickup_address="Dummy Street 123",
        pickup_city="Chennai",
        pickup_state="Tamil Nadu",
        pickup_pin="600001",
        requested_date=date.today(),
        status=PickupStatus.PENDING,
        idempotency_key="dummy-invalid-state"
    )
    db.add(pickup)
    db.commit()

    # Invalid: PENDING -> PICKED_UP
    with pytest.raises(Exception) as excinfo:
        transition_pickup_status(db, pickup, PickupStatus.PICKED_UP, actor_user=ag1_user)
    assert "Cannot transition pickup from PENDING to PICKED_UP" in str(excinfo.value)

    # Set status to PICKED_UP directly to test terminal state immutability
    pickup.status = PickupStatus.PICKED_UP
    db.commit()

    # Invalid: PICKED_UP -> CANCELLED
    with pytest.raises(Exception) as excinfo:
        transition_pickup_status(db, pickup, PickupStatus.CANCELLED, actor_user=c1)
    assert "Cannot transition pickup from PICKED_UP to CANCELLED" in str(excinfo.value)

    # Invalid: PICKED_UP -> PENDING
    with pytest.raises(Exception) as excinfo:
        transition_pickup_status(db, pickup, PickupStatus.PENDING, actor_user=c1)
    assert "Cannot transition pickup from PICKED_UP to PENDING" in str(excinfo.value)


def test_cancellation_by_citizen(client, seed_users):
    c1 = seed_users["citizen1"]
    headers_c1 = auth_header_for_user(c1)

    # Book Parcel
    p_resp = client.post("/api/v1/parcels", json={
        "receiver_name": "Meera Sen",
        "receiver_phone": "9876543210",
        "destination_address": "88 Park Avenue, Block C",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 1.0,
        "parcel_type": "DOCUMENT",
        "priority": "STANDARD"
    }, headers=headers_c1)
    parcel_id = p_resp.json()["data"]["id"]

    # Request Pickup
    pickup_resp = client.post("/api/v1/pickups", json={
        "parcel_id": parcel_id,
        "pickup_address": "Door 12, Park Street",
        "pickup_city": "Chennai",
        "pickup_state": "Tamil Nadu",
        "pickup_pin": "600001",
        "requested_date": str(date.today())
    }, headers={**headers_c1, "Idempotency-Key": "test-key-cancel-1"})
    pickup_id = pickup_resp.json()["data"]["id"]

    # Citizen cancels assigned pickup (ASSIGNED -> CANCELLED)
    cancel_resp = client.post(f"/api/v1/pickups/{pickup_id}/cancel", headers=headers_c1)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["data"]["status"] == "CANCELLED"
