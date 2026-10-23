import sys
import os
import uuid
from datetime import date

# Set DATABASE_URL to local sqlite if Postgres is not running
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///./smart_postal.db"

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))

from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal
from app.models.delivery_agent import DeliveryAgent

client = TestClient(app)

def run_e2e_verification():
    print("=================================================================")
    print("STARTING COMPLETE MODULE 1 END-TO-END VERIFICATION SCENARIO")
    print("=================================================================")

    # 1. Register new citizen
    citizen_email = f"citizen.test.{uuid.uuid4().hex[:6]}@example.com"
    print(f"\n[Step 1] Registering citizen: {citizen_email}...")
    reg_resp = client.post("/api/v1/auth/register", json={
        "name": "Kavita Ramachandran",
        "email": citizen_email,
        "phone": "9876543210",
        "password": "Password@123"
    })
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    reg_data = reg_resp.json()["data"]
    assert reg_data["role"] == "CITIZEN"
    print(f" Citizen registered successfully (Role: {reg_data['role']}, ID: {reg_data['id']})")

    # 2. Login as citizen
    print("\n[Step 2] Logging in as citizen...")
    login_resp = client.post("/api/v1/auth/login", json={
        "email": citizen_email,
        "password": "Password@123"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["access_token"]
    citizen_headers = {"Authorization": f"Bearer {token}"}
    print(" Logged in successfully. JWT Token acquired.")

    # 3. Create parcel
    print("\n[Step 3] Booking consignment parcel...")
    parcel_resp = client.post("/api/v1/parcels", json={
        "receiver_name": "Siddharth Rao",
        "receiver_phone": "9876543299",
        "destination_address": "45 Lakeview Enclave, Mount Road",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 2.5,
        "parcel_type": "SMALL_PARCEL",
        "priority": "EXPRESS"
    }, headers=citizen_headers)
    assert parcel_resp.status_code == 201
    parcel = parcel_resp.json()["data"]
    tracking_id = parcel["tracking_id"]
    parcel_id = parcel["id"]
    print(f" Consignment booked successfully!")
    print(f"   Prototype Tracking ID: {tracking_id}")
    assert tracking_id.startswith("GPM-2026-")

    # 4. Schedule doorstep pickup (Idempotent submission)
    print("\n[Step 4] Requesting doorstep pickup for PIN 600001...")
    idempotency_key = str(uuid.uuid4())
    pickup_payload = {
        "parcel_id": parcel_id,
        "pickup_address": "Flat 302, Green Meadows, Anna Nagar",
        "pickup_city": "Chennai",
        "pickup_state": "Tamil Nadu",
        "pickup_pin": "600001",
        "requested_date": str(date.today())
    }
    pickup_resp = client.post(
        "/api/v1/pickups",
        json=pickup_payload,
        headers={**citizen_headers, "Idempotency-Key": idempotency_key}
    )
    assert pickup_resp.status_code == 201
    pickup = pickup_resp.json()["data"]
    pickup_id = pickup["id"]
    assigned_agent_id = pickup["assigned_agent_id"]
    status_initial = pickup["status"]
    print(f" Pickup Request #{pickup_id} created.")
    print(f"   Current Status: {status_initial}")
    print(f"   Assigned Agent: {assigned_agent_id}")

    # 5. Verify duplicate idempotency submission
    print("\n[Step 5] Testing idempotency - re-submitting identical Idempotency-Key...")
    duplicate_resp = client.post(
        "/api/v1/pickups",
        json=pickup_payload,
        headers={**citizen_headers, "Idempotency-Key": idempotency_key}
    )
    assert duplicate_resp.status_code == 201
    dup_pickup = duplicate_resp.json()["data"]
    assert dup_pickup["id"] == pickup_id, "Idempotency failed: created duplicate ID"
    print(" Idempotency confirmed: Exact existing pickup record returned.")

    # 6. Check agent assignment details & Agent Login
    print("\n[Step 6] Logging in as Assigned Delivery Agent...")
    agent_login_resp = client.post("/api/v1/auth/login", json={
        "email": "agent.chennai@postal.gov.in",
        "password": "Agent@12345"
    })
    assert agent_login_resp.status_code == 200
    agent_token = agent_login_resp.json()["data"]["access_token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    print(" Agent authenticated successfully.")

    # 7. Agent views assigned pickups
    print("\n[Step 7] Agent viewing assigned pickups list...")
    agent_list_resp = client.get("/api/v1/agent/pickups", headers=agent_headers)
    assert agent_list_resp.status_code == 200
    agent_pickups = agent_list_resp.json()["data"]
    matching_pickup = next((p for p in agent_pickups if p["id"] == pickup_id), None)
    assert matching_pickup is not None, "Pickup not found in agent assigned list"
    print(f" Verified pickup #{pickup_id} is present in agent's workspace.")

    # 8. Agent accepts pickup (ASSIGNED -> ACCEPTED)
    print("\n[Step 8] Agent accepting pickup (ASSIGNED -> ACCEPTED)...")
    accept_resp = client.post(
        f"/api/v1/agent/pickups/{pickup_id}/accept",
        json={"reason": "Agent on route to collection point"},
        headers=agent_headers
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["data"]["status"] == "ACCEPTED"
    print(" Pickup transitioned to ACCEPTED.")

    # 9. Agent completes pickup (ACCEPTED -> PICKED_UP)
    print("\n[Step 9] Agent marking pickup as PICKED_UP (ACCEPTED -> PICKED_UP)...")
    complete_resp = client.post(
        f"/api/v1/agent/pickups/{pickup_id}/complete",
        json={"reason": "Parcel verified and collected from doorstep"},
        headers=agent_headers
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["data"]["status"] == "PICKED_UP"
    print(" Pickup transitioned to PICKED_UP.")

    # 10. Verify audit history trail
    print("\n[Step 10] Verifying immutable status history audit trail...")
    details_resp = client.get(f"/api/v1/pickups/{pickup_id}", headers=citizen_headers)
    assert details_resp.status_code == 200
    history = details_resp.json()["data"]["history"]
    print(f" Total history records found: {len(history)}")
    for h in history:
        print(f"   [{h['created_at'][:19]}] {h['old_status'] or 'INITIAL'} -> {h['new_status']} | By: {h['changed_by_role']} | {h['reason']}")
    assert len(history) >= 3

    # 11. Verify IDOR protection: Another citizen cannot access this pickup
    print("\n[Step 11] Testing IDOR protection with a different citizen...")
    other_reg = client.post("/api/v1/auth/register", json={
        "name": "Unauthorized Citizen",
        "email": f"other.{uuid.uuid4().hex[:6]}@example.com",
        "phone": "9876543211",
        "password": "Password@123"
    })
    other_token = client.post("/api/v1/auth/login", json={
        "email": other_reg.json()["data"]["email"],
        "password": "Password@123"
    }).json()["data"]["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    idor_resp = client.get(f"/api/v1/pickups/{pickup_id}", headers=other_headers)
    assert idor_resp.status_code == 403
    assert idor_resp.json()["error"]["code"] == "ACCESS_DENIED"
    print(" IDOR attempt successfully blocked: 403 ACCESS_DENIED.")

    # 12. Verify invalid state transition rejection (PICKED_UP -> CANCELLED)
    print("\n[Step 12] Testing invalid state transition rejection (PICKED_UP -> CANCELLED)...")
    invalid_cancel_resp = client.post(f"/api/v1/pickups/{pickup_id}/cancel", headers=citizen_headers)
    assert invalid_cancel_resp.status_code == 400
    assert invalid_cancel_resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
    print(" Invalid transition correctly rejected: 400 INVALID_STATE_TRANSITION.")

    print("\n=================================================================")
    print("MODULE 1 END-TO-END VERIFICATION COMPLETED SUCCESSFULLY (100% PASS)")
    print("=================================================================")

if __name__ == "__main__":
    run_e2e_verification()
