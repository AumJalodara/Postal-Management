import pytest
from datetime import date, timedelta
from tests.conftest import auth_header_for_user


def test_public_tracking_timeline(client, seed_users):
    """Public tracking returns masked info and chronological events."""
    c1 = seed_users["citizen1"]
    headers = auth_header_for_user(c1)

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Rohan Gupta",
        "receiver_phone": "9876543210",
        "destination_address": "12 Connaught Place Outer Circle",
        "destination_city": "New Delhi",
        "destination_state": "Delhi",
        "destination_pin": "110001",
        "weight": 1.2,
        "parcel_type": "SMALL_PARCEL",
        "priority": "EXPRESS"
    }, headers=headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    res = client.get(f"/api/v1/parcels/{tracking_id}/tracking")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["tracking_id"] == tracking_id
    assert data["current_status"] == "BOOKED"
    assert data["destination_city"] == "New Delhi"
    assert "*" in data["receiver_masked"]
    assert len(data["timeline"]) >= 1


def test_agent_advances_parcel_tracking_states(client, seed_users):
    """Agent sequentially advances parcel status through valid state machine transitions."""
    c1 = seed_users["citizen1"]
    agent_user = seed_users["agent1_user"]
    agent_headers = auth_header_for_user(agent_user)
    c1_headers = auth_header_for_user(c1)

    # 1. Create parcel
    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Ananya Roy",
        "receiver_phone": "9876511223",
        "destination_address": "88 Park Street Central Avenue",
        "destination_city": "Kolkata",
        "destination_state": "West Bengal",
        "destination_pin": "700016",
        "weight": 0.5,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=c1_headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    # 2. Transition BOOKED -> PICKED_UP
    step1 = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "PICKED_UP",
        "location_label": "Kolkata Local Office",
        "description": "Parcel picked up from local branch"
    }, headers=agent_headers)
    assert step1.status_code == 200
    assert step1.json()["data"]["new_status"] == "PICKED_UP"

    # 3. Transition PICKED_UP -> IN_TRANSIT
    step2 = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "IN_TRANSIT",
        "location_label": "Eastern Sorting Center",
        "description": "Dispatched to regional hub"
    }, headers=agent_headers)
    assert step2.status_code == 200
    assert step2.json()["data"]["new_status"] == "IN_TRANSIT"

    # 4. Transition IN_TRANSIT -> ARRIVED_AT_HUB
    step3 = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "ARRIVED_AT_HUB",
        "location_label": "Kolkata NSH Hub",
        "description": "Processed at National Sorting Hub"
    }, headers=agent_headers)
    assert step3.status_code == 200
    assert step3.json()["data"]["new_status"] == "ARRIVED_AT_HUB"

    # 5. Transition ARRIVED_AT_HUB -> OUT_FOR_DELIVERY
    step4 = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "OUT_FOR_DELIVERY",
        "location_label": "Park Street Sub-Post Office",
        "description": "Out for delivery with delivery agent"
    }, headers=agent_headers)
    assert step4.status_code == 200
    assert step4.json()["data"]["new_status"] == "OUT_FOR_DELIVERY"

    # 6. Transition OUT_FOR_DELIVERY -> DELIVERY_ATTEMPTED
    step5 = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "DELIVERY_ATTEMPTED",
        "location_label": "Park Street 700016",
        "description": "Door locked; reattempt scheduled"
    }, headers=agent_headers)
    assert step5.status_code == 200
    assert step5.json()["data"]["new_status"] == "DELIVERY_ATTEMPTED"

    # 7. Transition DELIVERY_ATTEMPTED -> OUT_FOR_DELIVERY
    step6 = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "OUT_FOR_DELIVERY",
        "location_label": "Park Street Sub-Post Office",
        "description": "Re-dispatched for delivery"
    }, headers=agent_headers)
    assert step6.status_code == 200
    assert step6.json()["data"]["new_status"] == "OUT_FOR_DELIVERY"

    # Verify complete timeline
    events_res = client.get(f"/api/v1/parcels/{tracking_id}/events")
    assert events_res.status_code == 200
    events = events_res.json()["data"]
    statuses = [e["new_status"] for e in events]
    assert statuses == [
        "BOOKED",
        "PICKED_UP",
        "IN_TRANSIT",
        "ARRIVED_AT_HUB",
        "OUT_FOR_DELIVERY",
        "DELIVERY_ATTEMPTED",
        "OUT_FOR_DELIVERY"
    ]


def test_invalid_tracking_transitions(client, seed_users):
    """Invalid transitions are rejected with 400 Bad Request."""
    c1 = seed_users["citizen1"]
    agent_user = seed_users["agent1_user"]
    agent_headers = auth_header_for_user(agent_user)
    c1_headers = auth_header_for_user(c1)

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Test Invalid",
        "receiver_phone": "9876543210",
        "destination_address": "123 Test Invalid Road Area",
        "destination_city": "Mumbai",
        "destination_state": "Maharashtra",
        "destination_pin": "400001",
        "weight": 1.0,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=c1_headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    # Invalid: BOOKED -> ARRIVED_AT_HUB (skipping PICKED_UP, IN_TRANSIT)
    bad_res = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "ARRIVED_AT_HUB",
        "location_label": "Mumbai Hub"
    }, headers=agent_headers)
    assert bad_res.status_code == 400
    assert bad_res.json()["error"]["code"] == "INVALID_TRACKING_TRANSITION"


def test_direct_delivery_without_otp_prohibited(client, seed_users):
    """Attempting to transition directly to DELIVERED via events endpoint is blocked."""
    c1 = seed_users["citizen1"]
    agent_user = seed_users["agent1_user"]
    agent_headers = auth_header_for_user(agent_user)
    c1_headers = auth_header_for_user(c1)

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Test Delivery Lock",
        "receiver_phone": "9876543210",
        "destination_address": "456 Delivery Street Colony",
        "destination_city": "Mumbai",
        "destination_state": "Maharashtra",
        "destination_pin": "400001",
        "weight": 1.0,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=c1_headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    res = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "DELIVERED",
        "location_label": "Mumbai Facility"
    }, headers=agent_headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "DELIVERY_NOT_ALLOWED"


def test_citizen_cannot_post_tracking_events(client, seed_users):
    """Citizen role cannot update tracking events (403 Forbidden)."""
    c1 = seed_users["citizen1"]
    c1_headers = auth_header_for_user(c1)

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Test RBAC",
        "receiver_phone": "9876543210",
        "destination_address": "789 Protected Road Lane",
        "destination_city": "Mumbai",
        "destination_state": "Maharashtra",
        "destination_pin": "400001",
        "weight": 1.0,
        "parcel_type": "DOCUMENT",
        "priority": "STANDARD"
    }, headers=c1_headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    res = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "PICKED_UP",
        "location_label": "Local Hub"
    }, headers=c1_headers)
    assert res.status_code == 403


def test_doorstep_pickup_syncs_tracking_status(client, seed_users):
    """Completing a doorstep pickup automatically advances parcel to PICKED_UP and creates event."""
    c1 = seed_users["citizen1"]
    agent_user = seed_users["agent1_user"]
    c1_headers = auth_header_for_user(c1)
    agent_headers = auth_header_for_user(agent_user)

    # 1. Book parcel
    parcel_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Sync Test",
        "receiver_phone": "9876543210",
        "destination_address": "123 Main Street Extension",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600002",
        "weight": 2.0,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=c1_headers)
    assert parcel_res.status_code == 201
    parcel_id = parcel_res.json()["data"]["id"]
    tracking_id = parcel_res.json()["data"]["tracking_id"]

    # 2. Book doorstep pickup
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    pickup_res = client.post("/api/v1/pickups", json={
        "parcel_id": parcel_id,
        "pickup_address": "12 Gandhi Road Cross Street",
        "pickup_city": "Chennai",
        "pickup_state": "Tamil Nadu",
        "pickup_pin": "600001",
        "requested_date": tomorrow
    }, headers={**c1_headers, "Idempotency-Key": "test-key-sync-1"})
    assert pickup_res.status_code == 201
    pickup_id = pickup_res.json()["data"]["id"]

    # 3. Agent accepts and completes pickup
    client.post(f"/api/v1/agent/pickups/{pickup_id}/accept", headers=agent_headers)
    complete_res = client.post(f"/api/v1/agent/pickups/{pickup_id}/complete", headers=agent_headers)
    assert complete_res.status_code == 200

    # 4. Verify parcel status is now PICKED_UP
    tracking_res = client.get(f"/api/v1/parcels/{tracking_id}/tracking")
    assert tracking_res.json()["data"]["current_status"] == "PICKED_UP"

    # 5. Verify timeline has BOOKED and PICKED_UP events
    timeline = tracking_res.json()["data"]["timeline"]
    assert len(timeline) == 2
    assert timeline[0]["new_status"] == "BOOKED"
    assert timeline[1]["new_status"] == "PICKED_UP"
