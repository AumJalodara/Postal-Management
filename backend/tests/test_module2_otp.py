import pytest
from tests.conftest import auth_header_for_user


def advance_to_out_for_delivery(client, parcel_tracking_id, agent_headers):
    """Helper to advance a parcel to OUT_FOR_DELIVERY status."""
    client.post(f"/api/v1/parcels/{parcel_tracking_id}/events", json={
        "new_status": "PICKED_UP",
        "location_label": "Local Hub Office"
    }, headers=agent_headers)
    client.post(f"/api/v1/parcels/{parcel_tracking_id}/events", json={
        "new_status": "IN_TRANSIT",
        "location_label": "Sorting Hub Office"
    }, headers=agent_headers)
    client.post(f"/api/v1/parcels/{parcel_tracking_id}/events", json={
        "new_status": "ARRIVED_AT_HUB",
        "location_label": "Destination Hub Office"
    }, headers=agent_headers)
    res = client.post(f"/api/v1/parcels/{parcel_tracking_id}/events", json={
        "new_status": "OUT_FOR_DELIVERY",
        "location_label": "Delivery Office Branch"
    }, headers=agent_headers)
    assert res.status_code == 200
    assert res.json()["data"]["new_status"] == "OUT_FOR_DELIVERY"


def test_otp_generation_requires_out_for_delivery(client, seed_users):
    """Requesting OTP on a parcel that is only BOOKED fails with 400."""
    c1 = seed_users["citizen1"]
    headers = auth_header_for_user(c1)

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "OTP Premature Test",
        "receiver_phone": "9876543210",
        "destination_address": "123 Test Road Extension Area",
        "destination_city": "Mumbai",
        "destination_state": "Maharashtra",
        "destination_pin": "400001",
        "weight": 1.0,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    otp_res = client.post(f"/api/v1/parcels/{tracking_id}/delivery-otp", headers=headers)
    assert otp_res.status_code == 400
    assert otp_res.json()["error"]["code"] == "DELIVERY_NOT_ALLOWED"


def test_otp_generation_success_and_format(client, seed_users):
    """When OUT_FOR_DELIVERY, OTP is generated, hashed, and test_otp is returned in test env."""
    c1 = seed_users["citizen1"]
    agent_user = seed_users["agent1_user"]
    c1_headers = auth_header_for_user(c1)
    agent_headers = auth_header_for_user(agent_user)

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "OTP Success Test",
        "receiver_phone": "9876543210",
        "destination_address": "456 Test Road Extension Area",
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
    otp_data = otp_res.json()["data"]

    assert otp_data["tracking_id"] == tracking_id
    assert otp_data["test_otp"] is not None
    assert len(otp_data["test_otp"]) == 6
    assert otp_data["test_otp"].isdigit()


def test_otp_attempt_limits_and_lockout(client, seed_users):
    """Submitting incorrect OTP decrements attempts and locks out after 5 failures."""
    c1 = seed_users["citizen1"]
    agent_user = seed_users["agent1_user"]
    c1_headers = auth_header_for_user(c1)
    agent_headers = auth_header_for_user(agent_user)

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "OTP Lockout Test",
        "receiver_phone": "9876543210",
        "destination_address": "789 Test Road Extension Area",
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

    # Generate OTP
    otp_res = client.post(f"/api/v1/parcels/{tracking_id}/delivery-otp", headers=agent_headers)
    assert otp_res.status_code == 200
    real_otp = otp_res.json()["data"]["test_otp"]
    fake_otp = "000000" if real_otp != "000000" else "111111"

    # Attempt 1 through 5 with fake OTP
    for attempt in range(1, 6):
        verify_res = client.post(f"/api/v1/parcels/{tracking_id}/verify-delivery", json={
            "otp": fake_otp
        }, headers=agent_headers)
        assert verify_res.status_code == 400
        if attempt < 5:
            assert verify_res.json()["error"]["code"] == "OTP_INVALID"
            expected_remaining = 5 - attempt
            assert f"Remaining attempts: {expected_remaining}" in verify_res.json()["error"]["message"]

    # 6th attempt should be blocked due to attempt exhaustion
    verify_res6 = client.post(f"/api/v1/parcels/{tracking_id}/verify-delivery", json={
        "otp": real_otp
    }, headers=agent_headers)
    assert verify_res6.status_code == 400
    assert verify_res6.json()["error"]["code"] == "OTP_ATTEMPT_LIMIT_EXCEEDED"


def test_unauthorized_agent_cannot_generate_otp_outside_service_area(client, seed_users):
    """
    Security Regression Test (ISSUE-02):
    Agent 1 (service_area 600001) cannot generate OTP for a parcel destined for Delhi (110001).
    Must be rejected with 403 Forbidden.
    """
    c1 = seed_users["citizen1"]
    agent_user = seed_users["agent1_user"]
    c1_headers = auth_header_for_user(c1)
    agent_headers = auth_header_for_user(agent_user)

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Delhi Recipient",
        "receiver_phone": "9876543210",
        "destination_address": "12 Connaught Place Area",
        "destination_city": "New Delhi",
        "destination_state": "Delhi",
        "destination_pin": "110001",
        "weight": 1.0,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=c1_headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    # Advance status using admin (or transit)
    admin_headers = auth_header_for_user(seed_users["admin"])
    advance_to_out_for_delivery(client, tracking_id, admin_headers)

    # Agent 1 (service area 600001) tries to generate OTP for Delhi parcel (110001)
    otp_res = client.post(f"/api/v1/parcels/{tracking_id}/delivery-otp", headers=agent_headers)
    assert otp_res.status_code == 403
    assert otp_res.json()["error"]["code"] == "ACCESS_DENIED"

