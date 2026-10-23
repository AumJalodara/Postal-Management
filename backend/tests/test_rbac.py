import pytest
from tests.conftest import auth_header_for_user


def test_citizen_cannot_access_agent_endpoints(client, seed_users):
    headers = auth_header_for_user(seed_users["citizen1"])
    response = client.get("/api/v1/agent/pickups", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_citizen_cannot_view_another_citizens_parcel(client, seed_users):
    headers1 = auth_header_for_user(seed_users["citizen1"])
    headers2 = auth_header_for_user(seed_users["citizen2"])

    # Citizen 1 books a parcel
    payload = {
        "receiver_name": "Deepak Patel",
        "receiver_phone": "9876543299",
        "destination_address": "45 Lake Road, Near Station",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 2.5,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }
    create_resp = client.post("/api/v1/parcels", json=payload, headers=headers1)
    assert create_resp.status_code == 201
    tracking_id = create_resp.json()["data"]["tracking_id"]

    # Citizen 2 tries to access Citizen 1's parcel
    forbidden_resp = client.get(f"/api/v1/parcels/{tracking_id}", headers=headers2)
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.json()["error"]["code"] == "ACCESS_DENIED"


def test_sender_id_derived_from_jwt_not_body(client, seed_users):
    headers1 = auth_header_for_user(seed_users["citizen1"])
    c1 = seed_users["citizen1"]

    # Client maliciously includes sender_id = 9999
    payload = {
        "sender_id": 9999,
        "receiver_name": "Rohan Verma",
        "receiver_phone": "9876543299",
        "destination_address": "78 Ring Road, Sector 5",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 1.0,
        "parcel_type": "DOCUMENT",
        "priority": "EXPRESS"
    }
    resp = client.post("/api/v1/parcels", json=payload, headers=headers1)
    assert resp.status_code == 201
    # The stored sender_id must be c1.id, not 9999
    assert resp.json()["data"]["sender_id"] == c1.id
