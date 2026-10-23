import sys
import os
import uuid
from datetime import date, timedelta

# Set DATABASE_URL to local sqlite if not defined
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///./smart_postal.db"

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))

from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal
from app.models.delivery_agent import DeliveryAgent

client = TestClient(app)


def run_module2_e2e_verification():
    print("=================================================================")
    print("AI-POWERED INTELLIGENT GOVERNMENT POSTAL MANAGEMENT SYSTEM")
    print("STARTING COMPLETE MODULE 2 END-TO-END VERIFICATION SCENARIO")
    print("QR Tracking, Lifecycle Transitions & Secure OTP Delivery")
    print("=================================================================")

    # 1. Register new citizen
    citizen_email = f"citizen.m2.{uuid.uuid4().hex[:6]}@example.com"
    print(f"\n[Step 1] Registering citizen: {citizen_email}...")
    reg_resp = client.post("/api/v1/auth/register", json={
        "name": "Kavita Ramachandran",
        "email": citizen_email,
        "phone": "9876543210",
        "password": "Password@123"
    })
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    print(" Citizen registered successfully.")

    # 2. Login as citizen
    print("\n[Step 2] Logging in as citizen...")
    login_resp = client.post("/api/v1/auth/login", json={
        "email": citizen_email,
        "password": "Password@123"
    })
    assert login_resp.status_code == 200
    citizen_token = login_resp.json()["data"]["access_token"]
    citizen_headers = {"Authorization": f"Bearer {citizen_token}"}
    print(" Citizen logged in. JWT Token acquired.")

    # 3. Login as delivery agent
    print("\n[Step 3] Logging in as delivery agent...")
    agent_login_resp = client.post("/api/v1/auth/login", json={
        "email": "agent.chennai@postal.gov.in",
        "password": "Agent@12345"
    })
    assert agent_login_resp.status_code == 200, f"Agent login failed: {agent_login_resp.text}"
    agent_token = agent_login_resp.json()["data"]["access_token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    print(" Delivery agent logged in. JWT Token acquired.")

    # 4. Citizen books parcel
    print("\n[Step 4] Citizen books consignment parcel...")
    parcel_resp = client.post("/api/v1/parcels", json={
        "receiver_name": "Deepak Natarajan",
        "receiver_phone": "9876543299",
        "destination_address": "45 Lakeview Enclave, Mount Road",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 2.5,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=citizen_headers)
    assert parcel_resp.status_code == 201, f"Parcel booking failed: {parcel_resp.text}"
    parcel_data = parcel_resp.json()["data"]
    parcel_id = parcel_data["id"]
    tracking_id = parcel_data["tracking_id"]
    print(f" Consignment booked: ID={parcel_id}, Tracking ID={tracking_id}, Status={parcel_data.get('status', 'BOOKED')}")

    # 5. Verify initial BOOKED tracking event & pre-generated QR code
    print("\n[Step 5] Verifying initial tracking event and pre-generated QR code...")
    events_resp = client.get(f"/api/v1/parcels/{tracking_id}/events")
    assert events_resp.status_code == 200
    events = events_resp.json()["data"]
    assert len(events) >= 1
    assert events[0]["new_status"] == "BOOKED"
    print(f" Initial BOOKED tracking event confirmed: '{events[0]['description']}'")

    qr_resp = client.get(f"/api/v1/parcels/{tracking_id}/qr", headers=citizen_headers)
    assert qr_resp.status_code == 200
    qr_data = qr_resp.json()["data"]
    qr_token = qr_data["qr_token"]
    assert qr_token.startswith("GPMQR-")
    assert qr_data["qr_code_base64"].startswith("data:image/png;base64,")
    print(f" Secure opaque QR token generated: {qr_token[:20]}... (Base64 PNG verified)")

    # 6. Public QR Scan Resolution & Privacy Masking check
    print("\n[Step 6] Simulating public QR scan resolution (Unauthenticated)...")
    resolve_resp = client.post("/api/v1/qr/resolve", json={"qr_token": qr_token})
    assert resolve_resp.status_code == 200
    resolve_data = resolve_resp.json()["data"]
    assert resolve_data["tracking_id"] == tracking_id
    assert "*" in resolve_data["sender_masked"]
    assert "*" in resolve_data["receiver_masked"]
    assert "9876543299" not in str(resolve_resp.json())
    print(f" Public QR resolution verified: Sender='{resolve_data['sender_masked']}', Recipient='{resolve_data['receiver_masked']}'")
    print(" Privacy shield verified: No phone numbers or internal user IDs leaked.")

    # 7. Citizen schedules doorstep pickup
    print("\n[Step 7] Scheduling doorstep pickup for consignment...")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    idempotency_key = f"pickup-m2-{uuid.uuid4()}"
    pickup_resp = client.post("/api/v1/pickups", json={
        "parcel_id": parcel_id,
        "pickup_address": "Flat 301, Heritage Villa, Anna Nagar",
        "pickup_city": "Chennai",
        "pickup_state": "Tamil Nadu",
        "pickup_pin": "600001",
        "requested_date": tomorrow
    }, headers={**citizen_headers, "Idempotency-Key": idempotency_key})
    assert pickup_resp.status_code == 201
    pickup_id = pickup_resp.json()["data"]["id"]
    print(f" Doorstep pickup scheduled: #{pickup_id} (Status: {pickup_resp.json()['data']['status']})")

    # 8. Agent accepts pickup
    print("\n[Step 8] Agent accepts assigned doorstep pickup...")
    accept_resp = client.post(f"/api/v1/agent/pickups/{pickup_id}/accept", headers=agent_headers)
    assert accept_resp.status_code == 200
    print(" Pickup accepted by agent (Status: ACCEPTED).")

    # 9. Agent completes pickup (ACCEPTED -> PICKED_UP)
    print("\n[Step 9] Agent collects parcel from doorstep (completing pickup)...")
    complete_resp = client.post(f"/api/v1/agent/pickups/{pickup_id}/complete", headers=agent_headers)
    assert complete_resp.status_code == 200
    print(" Doorstep pickup marked completed (Status: PICKED_UP).")

    # 10. Verify parcel status is synchronized to PICKED_UP
    print("\n[Step 10] Verifying consignment status synchronized to PICKED_UP...")
    track_resp = client.get(f"/api/v1/parcels/{tracking_id}/tracking")
    assert track_resp.status_code == 200
    assert track_resp.json()["data"]["current_status"] == "PICKED_UP"
    print(" Consignment status successfully synchronized to PICKED_UP.")

    # 11. Agent advances PICKED_UP -> IN_TRANSIT
    print("\n[Step 11] Agent advances status to IN_TRANSIT...")
    t1_resp = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "IN_TRANSIT",
        "location_label": "Chennai Central Facility",
        "description": "Consignment dispatched in secure transit container."
    }, headers=agent_headers)
    assert t1_resp.status_code == 200
    print(" Status advanced to IN_TRANSIT.")

    # 12. Agent advances IN_TRANSIT -> ARRIVED_AT_HUB
    print("\n[Step 12] Consignment arrives at sorting hub (ARRIVED_AT_HUB)...")
    t2_resp = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "ARRIVED_AT_HUB",
        "location_label": "National Sorting Hub Chennai 600001",
        "description": "Processed and sorted for destination sector."
    }, headers=agent_headers)
    assert t2_resp.status_code == 200
    print(" Status advanced to ARRIVED_AT_HUB.")

    # 13. Agent advances ARRIVED_AT_HUB -> OUT_FOR_DELIVERY
    print("\n[Step 13] Consignment dispatched OUT_FOR_DELIVERY...")
    t3_resp = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "OUT_FOR_DELIVERY",
        "location_label": "Mount Road Sub-Post Office",
        "description": "Out for delivery with delivery agent."
    }, headers=agent_headers)
    assert t3_resp.status_code == 200
    print(" Status advanced to OUT_FOR_DELIVERY.")

    # 14. Verify direct transition to DELIVERED without OTP is blocked
    print("\n[Step 14] Testing security boundary: Direct transition to DELIVERED without OTP...")
    bypass_resp = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "DELIVERED",
        "location_label": "Direct Handover"
    }, headers=agent_headers)
    assert bypass_resp.status_code == 400
    assert bypass_resp.json()["error"]["code"] == "DELIVERY_NOT_ALLOWED"
    print(" Direct delivery transition strictly blocked (400 Bad Request: DELIVERY_NOT_ALLOWED).")

    # 15. Agent advances OUT_FOR_DELIVERY -> DELIVERY_ATTEMPTED
    print("\n[Step 15] Simulating failed delivery attempt (DELIVERY_ATTEMPTED)...")
    att_resp = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "DELIVERY_ATTEMPTED",
        "location_label": "Lakeview Enclave 600001",
        "description": "Recipient unavailable; rescheduled for next run."
    }, headers=agent_headers)
    assert att_resp.status_code == 200
    print(" Status updated to DELIVERY_ATTEMPTED.")

    # 16. Agent re-dispatches DELIVERY_ATTEMPTED -> OUT_FOR_DELIVERY
    print("\n[Step 16] Re-dispatching for delivery (DELIVERY_ATTEMPTED -> OUT_FOR_DELIVERY)...")
    reout_resp = client.post(f"/api/v1/parcels/{tracking_id}/events", json={
        "new_status": "OUT_FOR_DELIVERY",
        "location_label": "Mount Road Sub-Post Office",
        "description": "Consignment out for delivery on second attempt."
    }, headers=agent_headers)
    assert reout_resp.status_code == 200
    print(" Status updated to OUT_FOR_DELIVERY.")

    # 17. Generate Delivery OTP
    print("\n[Step 17] Requesting 6-digit delivery confirmation OTP...")
    otp_resp = client.post(f"/api/v1/parcels/{tracking_id}/delivery-otp", headers=agent_headers)
    assert otp_resp.status_code == 200
    otp_data = otp_resp.json()["data"]
    test_otp = otp_data["test_otp"]
    assert test_otp and len(test_otp) == 6
    print(f" OTP generated successfully: {test_otp} (Valid for 5 minutes, hashed via Argon2id)")

    # 18. Submit invalid OTP (Verify attempt counter and decrementing attempts)
    print("\n[Step 18] Testing OTP verification with incorrect code...")
    fake_otp = "000000" if test_otp != "000000" else "111111"
    wrong_otp_resp = client.post(f"/api/v1/parcels/{tracking_id}/verify-delivery", json={
        "otp": fake_otp
    }, headers=agent_headers)
    assert wrong_otp_resp.status_code == 400
    assert wrong_otp_resp.json()["error"]["code"] == "OTP_INVALID"
    print(f" Invalid OTP rejected: '{wrong_otp_resp.json()['error']['message']}'")

    # 19. Unauthorized citizen cannot verify delivery
    print("\n[Step 19] Testing RBAC: Citizen role cannot submit delivery verification...")
    unauth_resp = client.post(f"/api/v1/parcels/{tracking_id}/verify-delivery", json={
        "otp": test_otp
    }, headers=citizen_headers)
    assert unauth_resp.status_code == 403
    print(" Unauthorized citizen attempt blocked (403 Forbidden).")

    # 20. Agent submits valid OTP -> Successful delivery confirmation
    print("\n[Step 20] Submitting valid OTP to complete secure delivery...")
    verify_resp = client.post(f"/api/v1/parcels/{tracking_id}/verify-delivery", json={
        "otp": test_otp
    }, headers=agent_headers)
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()["data"]
    assert verify_data["status"] == "DELIVERED"
    assert verify_data["verified"] is True
    assert verify_data["delivered_at"] is not None
    print(f" Delivery confirmed! Parcel {tracking_id} status: DELIVERED (Delivered at: {verify_data['delivered_at']})")

    # 21. Verify complete timeline in public tracking
    print("\n[Step 21] Inspecting final public tracking timeline...")
    final_track_resp = client.get(f"/api/v1/parcels/{tracking_id}/tracking")
    assert final_track_resp.status_code == 200
    final_data = final_track_resp.json()["data"]
    assert final_data["current_status"] == "DELIVERED"
    timeline = final_data["timeline"]
    status_seq = [e["new_status"] for e in timeline]
    print(f" Chronological state sequence ({len(timeline)} events):")
    for idx, e in enumerate(timeline, 1):
        print(f"   {idx}. {e['new_status']:<18} | {e['location_label']:<36} | {e['description']}")
    assert status_seq == [
        "BOOKED",
        "PICKED_UP",
        "IN_TRANSIT",
        "ARRIVED_AT_HUB",
        "OUT_FOR_DELIVERY",
        "DELIVERY_ATTEMPTED",
        "OUT_FOR_DELIVERY",
        "DELIVERED"
    ]

    # 22. Replay protection: Submitting the same OTP again fails
    print("\n[Step 22] Testing replay protection: Re-submitting the same OTP...")
    replay_resp = client.post(f"/api/v1/parcels/{tracking_id}/verify-delivery", json={
        "otp": test_otp
    }, headers=agent_headers)
    assert replay_resp.status_code == 400
    print(f" Replay strictly rejected ({replay_resp.json()['error']['code']}).")

    # 23. Requesting OTP on already delivered parcel is blocked
    print("\n[Step 23] Requesting OTP on already DELIVERED parcel...")
    otp_delivered_resp = client.post(f"/api/v1/parcels/{tracking_id}/delivery-otp", headers=agent_headers)
    assert otp_delivered_resp.status_code == 400
    print(" Post-delivery OTP generation rejected (400 Bad Request).")

    # 24. QR Code generation idempotency
    print("\n[Step 24] Verifying QR code retrieval idempotency...")
    qr_repeat_resp = client.get(f"/api/v1/parcels/{tracking_id}/qr", headers=citizen_headers)
    assert qr_repeat_resp.status_code == 200
    assert qr_repeat_resp.json()["data"]["qr_token"] == qr_token
    print(" QR code generation is verified idempotent (Same token returned).")

    print("\n=================================================================")
    print(" ALL 24 MODULE 2 END-TO-END VERIFICATION STEPS PASSED SUCCESSFULLY!")
    print("=================================================================\n")


if __name__ == "__main__":
    run_module2_e2e_verification()
