import pytest
from tests.conftest import auth_header_for_user


def test_get_postal_states_endpoint(client):
    """Verify GET /api/v1/postal/states returns all 36 Indian States and UTs."""
    resp = client.get("/api/v1/postal/states")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 36
    assert "Tamil Nadu" in data
    assert "Maharashtra" in data
    assert "Delhi" in data


def test_get_postal_cities_endpoint(client):
    """Verify GET /api/v1/postal/cities returns districts and default PIN for selected state."""
    resp = client.get("/api/v1/postal/cities?state=Tamil%20Nadu")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["state"] == "Tamil Nadu"
    assert "Chennai" in data["cities"]
    assert data["default_pin"] == "600001"


def test_get_postal_pincodes_endpoint(client):
    """Verify GET /api/v1/postal/pincodes returns PIN codes for state and city."""
    resp = client.get("/api/v1/postal/pincodes?state=Tamil%20Nadu&city=Chennai&limit=20")
    assert resp.status_code == 200
    pins = resp.json()["data"]
    assert "600001" in pins
    assert len(pins) <= 20


def test_validate_address_endpoint(client):
    """Verify POST /api/v1/postal/validate-address checks state-city-PIN consistency."""
    # Valid pair
    valid_resp = client.post("/api/v1/postal/validate-address", json={
        "state": "Tamil Nadu",
        "city": "Chennai",
        "pin": "600001"
    })
    assert valid_resp.status_code == 200
    assert valid_resp.json()["data"]["is_valid"] is True

    # State mismatch
    mismatch_resp = client.post("/api/v1/postal/validate-address", json={
        "state": "Maharashtra",
        "city": "Mumbai",
        "pin": "600001"
    })
    assert mismatch_resp.status_code == 200
    res = mismatch_resp.json()["data"]
    assert res["is_valid"] is False
    assert res["mismatch_type"] == "STATE_MISMATCH"
    assert "Tamil Nadu" in res["message"]


def test_booking_blocks_state_pin_mismatch(client, seed_users):
    """Verify POST /api/v1/parcels rejects booking with mismatched state and PIN code."""
    citizen = seed_users["citizen1"]
    headers = auth_header_for_user(citizen)

    # Citizen selects Maharashtra but enters Chennai PIN 600001
    bad_resp = client.post("/api/v1/parcels", json={
        "receiver_name": "Mismatch Test User",
        "receiver_phone": "9876543210",
        "destination_address": "100 Marine Drive Roadway",
        "destination_city": "Mumbai",
        "destination_state": "Maharashtra",
        "destination_pin": "600001",  # Belongs to Tamil Nadu!
        "weight": 1.0,
        "parcel_type": "DOCUMENT",
        "priority": "STANDARD"
    }, headers=headers)

    assert bad_resp.status_code == 400
    error_data = bad_resp.json()["error"]
    assert error_data["code"] == "ADDRESS_STATE_MISMATCH"
