import pytest
from datetime import date

def test_unauthenticated_access(client):
    resp = client.get("/api/v1/operations/agents")
    assert resp.status_code == 401

def test_unauthorized_citizen_access(client, seed_users):
    c1 = seed_users["citizen1"]
    from tests.conftest import auth_header_for_user
    headers = auth_header_for_user(c1)
    
    resp = client.get("/api/v1/operations/agents", headers=headers)
    assert resp.status_code == 403

def test_authorized_admin_access(client, seed_users):
    admin = seed_users["admin"]
    from tests.conftest import auth_header_for_user
    headers = auth_header_for_user(admin)
    
    resp = client.get("/api/v1/operations/agents", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    data = resp.json()["data"]
    assert isinstance(data, list)

def test_get_agent_route_and_eta(client, seed_users, db):
    admin = seed_users["admin"]
    ag1 = seed_users["agent1"]
    c1 = seed_users["citizen1"]
    
    from tests.conftest import auth_header_for_user
    admin_headers = auth_header_for_user(admin)
    c1_headers = auth_header_for_user(c1)
    
    # Create a parcel and pickup so there's a route
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
    }, headers=c1_headers)
    parcel_id = p_resp.json()["data"]["id"]
    
    pickup_resp = client.post("/api/v1/pickups", json={
        "parcel_id": parcel_id,
        "pickup_address": "Door 10, South End Road",
        "pickup_city": "Chennai",
        "pickup_state": "Tamil Nadu",
        "pickup_pin": "600001",
        "requested_date": str(date.today())
    }, headers={**c1_headers, "Idempotency-Key": "test-ops-1"})
    
    assert pickup_resp.status_code == 201
    assert pickup_resp.json()["data"]["assigned_agent_id"] == ag1.id
    
    # 1. Get Route
    route_resp = client.get(f"/api/v1/operations/agents/{ag1.id}/route", headers=admin_headers)
    assert route_resp.status_code == 200
    route_data = route_resp.json()["data"]
    assert route_data["agent_id"] == ag1.id
    assert len(route_data["stops"]) == 1
    
    # 2. Get ETA
    eta_resp = client.get(f"/api/v1/operations/agents/{ag1.id}/eta", headers=admin_headers)
    assert eta_resp.status_code == 200
    eta_data = eta_resp.json()["data"]
    assert eta_data["agent_id"] == ag1.id
    assert eta_data["routable_stop_count"] == 1
    
    # 3. Get Detail
    detail_resp = client.get(f"/api/v1/operations/agents/{ag1.id}", headers=admin_headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()["data"]
    assert detail_data["agent"]["agent_id"] == ag1.id
    assert detail_data["route"]["agent_id"] == ag1.id
    assert detail_data["eta"]["agent_id"] == ag1.id

def test_pickups_list_with_filters(client, seed_users):
    admin = seed_users["admin"]
    ag1 = seed_users["agent1"]
    from tests.conftest import auth_header_for_user
    admin_headers = auth_header_for_user(admin)
    
    # Test valid filter
    resp = client.get(f"/api/v1/operations/pickups?agent_id={ag1.id}&status=ASSIGNED", headers=admin_headers)
    assert resp.status_code == 200
    
    # Test invalid status filter
    resp_inv = client.get(f"/api/v1/operations/pickups?status=INVALID_STATUS", headers=admin_headers)
    assert resp_inv.status_code == 400
    assert resp_inv.json()["error"]["code"] == "INVALID_STATUS"
