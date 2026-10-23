import concurrent.futures
from tests.conftest import auth_header_for_user


def test_concurrent_parcel_tracking_id_uniqueness(client, seed_users):
    headers = auth_header_for_user(seed_users["citizen1"])
    total_parcels = 50

    def create_single_parcel(idx):
        # Generate strictly valid Indian-formatted alphabetic name
        letter1 = chr(65 + (idx % 26))
        letter2 = chr(65 + ((idx // 26) % 26))
        receiver_name = f"Receiver {letter1} {letter2} Kumar"
        
        payload = {
            "receiver_name": receiver_name,
            "receiver_phone": "9876543210",
            "destination_address": f"Apartment {idx + 10}, Main Market Street",
            "destination_city": "Chennai",
            "destination_state": "Tamil Nadu",
            "destination_pin": "600001",
            "weight": 1.0,
            "parcel_type": "DOCUMENT",
            "priority": "STANDARD"
        }
        res = client.post("/api/v1/parcels", json=payload, headers=headers)
        return res

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_single_parcel, i) for i in range(total_parcels)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Verify all 50 requests succeeded
    assert len(results) == total_parcels
    tracking_ids = []
    for r in results:
        assert r.status_code == 201, f"Failed creation: {r.text}"
        data = r.json()["data"]
        tid = data["tracking_id"]
        assert tid.startswith("GPM-2026-")
        tracking_ids.append(tid)

    # Verify all 50 tracking IDs are completely unique
    unique_ids = set(tracking_ids)
    assert len(unique_ids) == total_parcels, f"Expected 50 unique tracking IDs, got {len(unique_ids)}"
