from datetime import date, datetime, timedelta, timezone
from app.models.delivery_agent import DeliveryAgent
from app.models.user import User
from app.models.enums import UserRole
from tests.conftest import auth_header_for_user

def test_operations_api_unauthorized_access(client, seed_users):
    c1 = seed_users["citizen1"]
    headers = auth_header_for_user(c1)
    
    # Citizen should be rejected
    resp = client.get("/api/v1/operations/agents", headers=headers)
    assert resp.status_code == 403
    
    # Unauthenticated should be rejected
    resp = client.get("/api/v1/operations/agents")
    assert resp.status_code == 401

def test_operations_agents_list_and_detail(client, seed_users):
    admin = seed_users["admin"]
    headers = auth_header_for_user(admin)
    ag1 = seed_users["agent1"]
    
    resp = client.get("/api/v1/operations/agents", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 2
    assert "agent_id" in data[0]
    
    resp = client.get(f"/api/v1/operations/agents/{ag1.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["agent"]["agent_id"] == ag1.id
    assert "route" in data
    assert "eta" in data

def test_operations_route_and_eta(client, seed_users):
    admin = seed_users["admin"]
    headers = auth_header_for_user(admin)
    ag1 = seed_users["agent1"]
    
    # Empty route initially
    resp = client.get(f"/api/v1/operations/agents/{ag1.id}/route", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["stops"]) == 0
    assert data["total_distance_km"] == 0
    
    resp = client.get(f"/api/v1/operations/agents/{ag1.id}/eta", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total_eta_minutes"] == 0
    
    # Check history endpoint contains route generated events
    h_resp = client.get("/api/v1/operations/history?event_type=ROUTE_GENERATED", headers=headers)
    assert h_resp.status_code == 200
    assert h_resp.json()["data"]["total_count"] >= 1

def test_operations_pickups(client, seed_users):
    admin = seed_users["admin"]
    headers = auth_header_for_user(admin)
    
    resp = client.get("/api/v1/operations/pickups", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    
def test_operations_history_filtering_pagination(client, seed_users):
    admin = seed_users["admin"]
    headers = auth_header_for_user(admin)
    
    resp = client.get("/api/v1/operations/history?page=1&page_size=2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert len(data["items"]) <= 2
    assert "total_count" in data

def test_operations_assistant_unauthorized(client, seed_users):
    c1 = seed_users["citizen1"]
    headers = auth_header_for_user(c1)
    resp = client.post("/api/v1/operations/assistant", json={"query": "hello"}, headers=headers)
    assert resp.status_code == 403

def test_operations_assistant_missing_key(client, seed_users, monkeypatch):
    admin = seed_users["admin"]
    headers = auth_header_for_user(admin)
    
    # Mock config to use groq but with empty key
    from app.config import settings
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    
    resp = client.post("/api/v1/operations/assistant", json={"query": "Which agent has the highest workload?"}, headers=headers)
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "AI_UNAVAILABLE"
    assert "GROQ_API_KEY environment variable is required" in resp.json()["error"]["message"]

def test_operations_assistant_mock_fallback_for_tests(client, seed_users, monkeypatch):
    admin = seed_users["admin"]
    headers = auth_header_for_user(admin)
    
    # For automated tests we use mock provider
    from app.config import settings
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    
    resp = client.post("/api/v1/operations/assistant", json={"query": "What is the workload?"}, headers=headers)
    assert resp.status_code == 200
    assert "data" in resp.json()
    assert "answer" in resp.json()["data"]


def test_operations_citizens_metrics_and_list(client, seed_users):
    admin = seed_users["admin"]
    headers = auth_header_for_user(admin)

    resp = client.get("/api/v1/operations/citizens", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "metrics" in data
    assert "citizens" in data
    assert data["metrics"]["total_registered_citizens"] >= 1
    assert isinstance(data["citizens"], list)
    first_cit = data["citizens"][0]
    assert "citizen_id" in first_cit
    assert "name" in first_cit
    assert "parcels_booked_count" in first_cit


def test_operations_citizen_parcels_endpoint(client, seed_users):
    admin = seed_users["admin"]
    headers = auth_header_for_user(admin)
    c1 = seed_users["citizen1"]

    resp = client.get(f"/api/v1/operations/citizens/{c1.id}/parcels", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)

