import pytest
from tests.conftest import auth_header_for_user
from tests.test_module2_otp import advance_to_out_for_delivery


def test_secure_delivery_verification_success(client, seed_users):
    """Agent verifies delivery with valid OTP; parcel transitions to DELIVERED."""
    c1 = seed_users["citizen1"]
    agent_user = seed_users["agent1_user"]
    c1_headers = auth_header_for_user(c1)
    agent_headers = auth_header_for_user(agent_user)

    # 1. Book parcel
    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Kavita Krishnamurthy",
        "receiver_phone": "9876543210",
        "destination_address": "55 Anna Salai Main Road",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 1.1,
        "parcel_type": "SMALL_PARCEL",
        "priority": "EXPRESS"
    }, headers=c1_headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    # 2. Advance to OUT_FOR_DELIVERY
    advance_to_out_for_delivery(client, tracking_id, agent_headers)

    # 3. Generate OTP
    otp_res = client.post(f"/api/v1/parcels/{tracking_id}/delivery-otp", headers=agent_headers)
    assert otp_res.status_code == 200
    otp = otp_res.json()["data"]["test_otp"]

    # 4. Agent submits OTP to confirm delivery
    verify_res = client.post(f"/api/v1/parcels/{tracking_id}/verify-delivery", json={
        "otp": otp
    }, headers=agent_headers)
    assert verify_res.status_code == 200
    verify_data = verify_res.json()["data"]

    assert verify_data["tracking_id"] == tracking_id
    assert verify_data["status"] == "DELIVERED"
    assert verify_data["verified"] is True
    assert verify_data["delivered_at"] is not None

    # 5. Verify tracking timeline shows DELIVERED as current and in history
    tracking_res = client.get(f"/api/v1/parcels/{tracking_id}/tracking")
    assert tracking_res.json()["data"]["current_status"] == "DELIVERED"
    timeline = tracking_res.json()["data"]["timeline"]
    assert timeline[-1]["new_status"] == "DELIVERED"
    assert "OTP verification" in timeline[-1]["description"]


def test_delivery_otp_replay_protection(client, seed_users):
    """Submitting the same OTP again after successful delivery is rejected."""
    c1 = seed_users["citizen1"]
    agent_user = seed_users["agent1_user"]
    c1_headers = auth_header_for_user(c1)
    agent_headers = auth_header_for_user(agent_user)

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Replay Test",
        "receiver_phone": "9876543210",
        "destination_address": "123 Test Replay Road Area",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 1.0,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=c1_headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    advance_to_out_for_delivery(client, tracking_id, agent_headers)

    otp_res = client.post(f"/api/v1/parcels/{tracking_id}/delivery-otp", headers=agent_headers)
    assert otp_res.status_code == 200
    otp = otp_res.json()["data"]["test_otp"]

    # First verification succeeds
    res1 = client.post(f"/api/v1/parcels/{tracking_id}/verify-delivery", json={"otp": otp}, headers=agent_headers)
    assert res1.status_code == 200

    # Replay attempt fails
    res2 = client.post(f"/api/v1/parcels/{tracking_id}/verify-delivery", json={"otp": otp}, headers=agent_headers)
    assert res2.status_code == 400


def test_citizen_cannot_verify_delivery(client, seed_users):
    """Citizen role cannot call verify-delivery (403 Forbidden)."""
    c1 = seed_users["citizen1"]
    agent_user = seed_users["agent1_user"]
    c1_headers = auth_header_for_user(c1)
    agent_headers = auth_header_for_user(agent_user)

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Delivery Test User",
        "receiver_phone": "9876543210",
        "destination_address": "456 Secured Route Street",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 1.0,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=c1_headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    advance_to_out_for_delivery(client, tracking_id, agent_headers)

    otp_res = client.post(f"/api/v1/parcels/{tracking_id}/delivery-otp", headers=agent_headers)
    assert otp_res.status_code == 200
    otp = otp_res.json()["data"]["test_otp"]

    # Citizen tries to call verify-delivery
    res = client.post(f"/api/v1/parcels/{tracking_id}/verify-delivery", json={"otp": otp}, headers=c1_headers)
    assert res.status_code == 403


def test_unauthorized_agent_cannot_verify_delivery_outside_service_area(client, seed_users):
    """
    Security Regression Test (ISSUE-02):
    Agent 1 (service_area 600001) cannot verify delivery for a parcel destined for Delhi (110001).
    Must be rejected with 403 Forbidden.
    """
    c1 = seed_users["citizen1"]
    agent_user = seed_users["agent1_user"]
    c1_headers = auth_header_for_user(c1)
    agent_headers = auth_header_for_user(agent_user)
    admin_headers = auth_header_for_user(seed_users["admin"])

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Delhi Recipient",
        "receiver_phone": "9876543210",
        "destination_address": "88 Connaught Place",
        "destination_city": "New Delhi",
        "destination_state": "Delhi",
        "destination_pin": "110001",
        "weight": 1.0,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=c1_headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    advance_to_out_for_delivery(client, tracking_id, admin_headers)

    # Admin generates OTP
    otp_res = client.post(f"/api/v1/parcels/{tracking_id}/delivery-otp", headers=admin_headers)
    assert otp_res.status_code == 200
    otp = otp_res.json()["data"]["test_otp"]

    # Unauthorized agent (600001) tries to verify delivery for 110001 parcel
    res = client.post(f"/api/v1/parcels/{tracking_id}/verify-delivery", json={"otp": otp}, headers=agent_headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "ACCESS_DENIED"

