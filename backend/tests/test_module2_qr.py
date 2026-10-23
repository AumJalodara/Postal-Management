import pytest
from tests.conftest import auth_header_for_user


def test_qr_generation_and_retrieval(client, seed_users):
    """Citizen books a parcel and retrieves its secure QR code."""
    c1 = seed_users["citizen1"]
    headers = auth_header_for_user(c1)

    # 1. Book parcel
    parcel_payload = {
        "receiver_name": "Amit Sharma",
        "receiver_phone": "9123456780",
        "destination_address": "123 Anna Salai",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600002",
        "weight": 1.5,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }
    create_res = client.post("/api/v1/parcels", json=parcel_payload, headers=headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    # 2. Retrieve QR code
    qr_res = client.get(f"/api/v1/parcels/{tracking_id}/qr", headers=headers)
    assert qr_res.status_code == 200
    qr_data = qr_res.json()["data"]

    assert qr_data["tracking_id"] == tracking_id
    assert qr_data["qr_token"].startswith("GPMQR-")
    assert qr_data["qr_code_base64"].startswith("data:image/png;base64,")
    assert "/track/qr/" in qr_data["payload_url"]


def test_qr_generation_idempotency(client, seed_users):
    """Repeated calls to QR endpoint return the same token without creating duplicates."""
    c1 = seed_users["citizen1"]
    headers = auth_header_for_user(c1)

    parcel_payload = {
        "receiver_name": "Suresh Raina",
        "receiver_phone": "9876500000",
        "destination_address": "45 MG Road",
        "destination_city": "Bengaluru",
        "destination_state": "Karnataka",
        "destination_pin": "560001",
        "weight": 2.0,
        "parcel_type": "MEDIUM_PARCEL",
        "priority": "EXPRESS"
    }
    create_res = client.post("/api/v1/parcels", json=parcel_payload, headers=headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    res1 = client.get(f"/api/v1/parcels/{tracking_id}/qr", headers=headers)
    res2 = client.post(f"/api/v1/parcels/{tracking_id}/qr", headers=headers)

    assert res1.json()["data"]["qr_token"] == res2.json()["data"]["qr_token"]


def test_public_qr_resolve_and_privacy_masking(client, seed_users):
    """Scanning a QR code publicly resolves tracking info with privacy masking."""
    c1 = seed_users["citizen1"]
    headers = auth_header_for_user(c1)

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Deepak Chahar",
        "receiver_phone": "9998887776",
        "destination_address": "77 Marina Beach Road",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600005",
        "weight": 0.8,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=headers)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    # Get QR token
    qr_res = client.get(f"/api/v1/parcels/{tracking_id}/qr", headers=headers)
    qr_token = qr_res.json()["data"]["qr_token"]

    # Public scan resolution (no auth header needed)
    resolve_res = client.post("/api/v1/qr/resolve", json={"qr_token": qr_token})
    assert resolve_res.status_code == 200
    data = resolve_res.json()["data"]

    assert data["tracking_id"] == tracking_id
    assert data["current_status"] == "BOOKED"
    assert data["destination_city"] == "Chennai"
    assert data["destination_pin"] == "600005"

    # Verify privacy masking
    assert "*" in data["sender_masked"]
    assert "*" in data["receiver_masked"]
    # Ensure raw phone numbers, passwords, internal user IDs are NOT leaked
    assert "9998887776" not in str(resolve_res.json())
    assert "password" not in str(resolve_res.json()).lower()

    # Timeline has at least initial BOOKED event
    assert len(data["timeline"]) >= 1
    assert data["timeline"][0]["new_status"] == "BOOKED"


def test_qr_resolve_invalid_token(client):
    """Resolving a non-existent or malformed token returns 404."""
    res = client.post("/api/v1/qr/resolve", json={"qr_token": "GPMQR-nonexistenttoken123"})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "QR_NOT_FOUND"


def test_qr_endpoint_rbac(client, seed_users):
    """Citizen 2 cannot access Citizen 1's QR generation endpoint."""
    c1 = seed_users["citizen1"]
    c2 = seed_users["citizen2"]
    headers1 = auth_header_for_user(c1)
    headers2 = auth_header_for_user(c2)

    create_res = client.post("/api/v1/parcels", json={
        "receiver_name": "Test Recipient",
        "receiver_phone": "9876543210",
        "destination_address": "Test Address",
        "destination_city": "Mumbai",
        "destination_state": "Maharashtra",
        "destination_pin": "400001",
        "weight": 1.0,
        "parcel_type": "DOCUMENT",
        "priority": "STANDARD"
    }, headers=headers1)
    assert create_res.status_code == 201
    tracking_id = create_res.json()["data"]["tracking_id"]

    # Citizen 2 attempts to get Citizen 1's QR
    res = client.get(f"/api/v1/parcels/{tracking_id}/qr", headers=headers2)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "ACCESS_DENIED"
