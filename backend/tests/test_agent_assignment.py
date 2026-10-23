from datetime import date, datetime, timedelta, timezone
from app.models.delivery_agent import DeliveryAgent
from app.models.user import User
from app.models.enums import UserRole
from app.auth.security import hash_password
from tests.conftest import auth_header_for_user


def test_agent_assignment_lowest_workload(client, seed_users):
    c1 = seed_users["citizen1"]
    ag1 = seed_users["agent1"]  # active_pickup_count = 0
    ag2 = seed_users["agent2"]  # active_pickup_count = 1
    headers = auth_header_for_user(c1)

    # 1. Book Parcel
    p_resp = client.post("/api/v1/parcels", json={
        "receiver_name": "Ajay Sharma",
        "receiver_phone": "9876543210",
        "destination_address": "Flat 4, South End Road",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 1.0,
        "parcel_type": "DOCUMENT",
        "priority": "STANDARD"
    }, headers=headers)
    parcel_id = p_resp.json()["data"]["id"]

    # 2. Request Pickup (PIN 600001)
    pickup_resp = client.post("/api/v1/pickups", json={
        "parcel_id": parcel_id,
        "pickup_address": "Door 10, South End Road",
        "pickup_city": "Chennai",
        "pickup_state": "Tamil Nadu",
        "pickup_pin": "600001",
        "requested_date": str(date.today())
    }, headers={**headers, "Idempotency-Key": "test-assignment-workload-1"})

    assert pickup_resp.status_code == 201
    pickup_data = pickup_resp.json()["data"]

    # ag1 had workload 0, ag2 had workload 1. Agent 1 MUST be chosen!
    assert pickup_data["assigned_agent_id"] == ag1.id
    assert pickup_data["status"] == "ASSIGNED"


def test_agent_assignment_tiebreaker_and_unavailable(client, seed_users, db):
    c1 = seed_users["citizen1"]
    headers = auth_header_for_user(c1)

    # Make ag1 unavailable
    ag1 = seed_users["agent1"]
    ag1.is_available = False
    # ag2 is available but PIN is 600001
    ag2 = seed_users["agent2"]
    ag2.is_available = True
    ag2.active_pickup_count = 0
    db.commit()

    # Book Parcel
    p_resp = client.post("/api/v1/parcels", json={
        "receiver_name": "Sanjay Kapoor",
        "receiver_phone": "9876543210",
        "destination_address": "Flat 8B, High Street",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 1.0,
        "parcel_type": "DOCUMENT",
        "priority": "STANDARD"
    }, headers=headers)
    parcel_id = p_resp.json()["data"]["id"]

    pickup_resp = client.post("/api/v1/pickups", json={
        "parcel_id": parcel_id,
        "pickup_address": "Door 20, High Street",
        "pickup_city": "Chennai",
        "pickup_state": "Tamil Nadu",
        "pickup_pin": "600001",
        "requested_date": str(date.today())
    }, headers={**headers, "Idempotency-Key": "test-assignment-unavailable-1"})

    # Since ag1 is unavailable, ag2 MUST be selected
    assert pickup_resp.json()["data"]["assigned_agent_id"] == ag2.id


def test_no_eligible_agent_remains_pending(client, seed_users):
    c1 = seed_users["citizen1"]
    headers = auth_header_for_user(c1)

    # Book parcel with a PIN that has no agent assigned (e.g. 500001 Hyderabad)
    p_resp = client.post("/api/v1/parcels", json={
        "receiver_name": "Venkatesh Rao",
        "receiver_phone": "9876543210",
        "destination_address": "Flat 5, Banjara Hills Road",
        "destination_city": "Hyderabad",
        "destination_state": "Telangana",
        "destination_pin": "500001",
        "weight": 1.0,
        "parcel_type": "DOCUMENT",
        "priority": "STANDARD"
    }, headers=headers)
    parcel_id = p_resp.json()["data"]["id"]

    pickup_resp = client.post("/api/v1/pickups", json={
        "parcel_id": parcel_id,
        "pickup_address": "Door 55, Banjara Hills",
        "pickup_city": "Hyderabad",
        "pickup_state": "Telangana",
        "pickup_pin": "500001",
        "requested_date": str(date.today())
    }, headers={**headers, "Idempotency-Key": "test-assignment-no-agent-1"})

    assert pickup_resp.status_code == 201
    pickup_data = pickup_resp.json()["data"]

    # No agent serves 500001, so must remain PENDING and assigned_agent_id is None
    assert pickup_data["status"] == "PENDING"
    assert pickup_data["assigned_agent_id"] is None


def test_agent_delivery_queue_filters_by_service_area(client, seed_users, db):
    """
    ISSUE-09 / ISSUE-11 Regression Test:
    Verify GET /api/v1/agent/deliveries strictly filters parcels by the agent's service area.
    """
    from app.models.parcel import Parcel
    from app.models.enums import ParcelTrackingStatus, ParcelType, Priority

    c1 = seed_users["citizen1"]
    ag1_user = seed_users["agent1_user"]
    ag_headers = auth_header_for_user(ag1_user)

    # 1. Parcel in Agent 1's service area (600001) in ARRIVED_AT_HUB status
    p1 = Parcel(
        tracking_id="IN600001001",
        sender_id=c1.id,
        receiver_name="Chennai Receiver",
        receiver_phone="9876543210",
        destination_address="12 Anna Salai",
        destination_city="Chennai",
        destination_state="Tamil Nadu",
        destination_pin="600001",
        weight=1.5,
        parcel_type=ParcelType.SMALL_PARCEL,
        priority=Priority.STANDARD,
        status="ARRIVED_AT_HUB",
        price=150.0
    )
    # 2. Parcel in Delhi (110001), outside Agent 1's service area
    p2 = Parcel(
        tracking_id="IN110001001",
        sender_id=c1.id,
        receiver_name="Delhi Receiver",
        receiver_phone="9876543211",
        destination_address="4 Connaught Place",
        destination_city="New Delhi",
        destination_state="Delhi",
        destination_pin="110001",
        weight=1.0,
        parcel_type=ParcelType.DOCUMENT,
        priority=Priority.STANDARD,
        status="ARRIVED_AT_HUB",
        price=100.0
    )
    db.add_all([p1, p2])
    db.commit()

    # Agent 1 fetches deliveries
    resp = client.get("/api/v1/agent/deliveries", headers=ag_headers)
    assert resp.status_code == 200
    parcels = resp.json()["data"]

    tracking_ids = [p["tracking_id"] for p in parcels]
    # p1 (600001) must be in queue
    assert "IN600001001" in tracking_ids
    # p2 (110001) must NOT be in queue
    assert "IN110001001" not in tracking_ids


def test_agent_status_transition_cross_area_forbidden(client, seed_users, db):
    """
    ISSUE-11 Regression Test:
    Agent cannot dispatch OUT_FOR_DELIVERY for a parcel outside their service area.
    """
    from app.models.parcel import Parcel
    from app.models.enums import ParcelType, Priority

    c1 = seed_users["citizen1"]
    ag1_user = seed_users["agent1_user"]
    ag_headers = auth_header_for_user(ag1_user)

    # Parcel in Delhi (110001), outside Agent 1's service area (600001)
    p_delhi = Parcel(
        tracking_id="IN110001002",
        sender_id=c1.id,
        receiver_name="Delhi Receiver",
        receiver_phone="9876543211",
        destination_address="4 Connaught Place",
        destination_city="New Delhi",
        destination_state="Delhi",
        destination_pin="110001",
        weight=1.0,
        parcel_type=ParcelType.DOCUMENT,
        priority=Priority.STANDARD,
        status="ARRIVED_AT_HUB",
        price=100.0
    )
    db.add(p_delhi)
    db.commit()

    # Attempt cross-area dispatch
    resp = client.post(
        f"/api/v1/agent/parcels/{p_delhi.tracking_id}/events",
        json={
            "new_status": "OUT_FOR_DELIVERY",
            "location_label": "Delhi Hub",
            "description": "Out for delivery"
        },
        headers=ag_headers
    )
    assert resp.status_code == 403
    err_body = resp.json()
    assert err_body["error"]["code"] == "ACCESS_DENIED"

