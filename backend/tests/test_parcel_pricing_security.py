from decimal import Decimal
import pytest
from app.models.enums import ParcelType, Priority, UserRole
from app.models.parcel import Parcel
from app.services.pricing_service import calculate_parcel_price, get_price_quote
from tests.conftest import auth_header_for_user


def test_pricing_service_tariff_calculations():
    """Verify tariff formulas for standard parcel types and priorities."""
    # Document 0.5kg Standard: 25 + (0.5 * 15) = 32.50
    doc_price = calculate_parcel_price(0.5, ParcelType.DOCUMENT, Priority.STANDARD)
    assert doc_price == Decimal("32.50")

    # Document 0.5kg Express: 32.50 * 1.5 = 48.75
    doc_exp_price = calculate_parcel_price(0.5, ParcelType.DOCUMENT, Priority.EXPRESS)
    assert doc_exp_price == Decimal("48.75")

    # Small Parcel 1.0kg Standard: 45 + (1.0 * 25) = 70.00
    sp_price = calculate_parcel_price(1.0, ParcelType.SMALL_PARCEL, Priority.STANDARD)
    assert sp_price == Decimal("70.00")

    # Medium Parcel 4.0kg Standard: 90 + (4.0 * 35) = 230.00
    mp_price = calculate_parcel_price(4.0, ParcelType.MEDIUM_PARCEL, Priority.STANDARD)
    assert mp_price == Decimal("230.00")

    # Large Parcel 12.0kg Express: (180 + (12.0 * 45)) * 1.5 = (180 + 540) * 1.5 = 1080.00
    lp_price = calculate_parcel_price(12.0, ParcelType.LARGE_PARCEL, Priority.EXPRESS)
    assert lp_price == Decimal("1080.00")


def test_quote_endpoint_server_side_calculation(client, seed_users):
    """Verify POST /api/v1/parcels/quote calculates price server-side."""
    citizen = seed_users["citizen1"]
    headers = auth_header_for_user(citizen)

    resp = client.post("/api/v1/parcels/quote", json={
        "weight": 2.0,
        "parcel_type": "SMALL_PARCEL",
        "priority": "STANDARD"
    }, headers=headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    # 45 + (2.0 * 25) = 95.00
    assert data["total_price"] == 95.00
    assert data["base_price"] == 45.00
    assert data["weight_charge"] == 50.00
    assert data["express_surcharge"] == 0.00
    assert data["currency"] == "INR"


def test_client_cannot_force_zero_or_arbitrary_price_on_booking(client, seed_users, db):
    """
    Security Test: Ensure client cannot specify price=0 or price=1.00 to cheat payment.
    The server MUST ignore client-supplied price and compute authoritative tariff.
    """
    citizen = seed_users["citizen1"]
    headers = auth_header_for_user(citizen)

    # Citizen tries to book with price=0.00
    resp_zero = client.post("/api/v1/parcels", json={
        "receiver_name": "Price Test Receiver",
        "receiver_phone": "9876543210",
        "destination_address": "123 Security Lane",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 1.0,
        "parcel_type": "DOCUMENT",
        "priority": "STANDARD",
        "price": 0.00  # Adversarial zero price
    }, headers=headers)

    assert resp_zero.status_code == 201
    parcel_zero = resp_zero.json()["data"]
    # Document 1.0kg: 25 + (1.0 * 15) = 40.00
    assert Decimal(str(parcel_zero["price"])) == Decimal("40.00")
    assert Decimal(str(parcel_zero["price"])) != Decimal("0.00")

    # Citizen tries to book with arbitrary fake price (0.01)
    resp_arb = client.post("/api/v1/parcels", json={
        "receiver_name": "Arbitrary Price Test",
        "receiver_phone": "9876543210",
        "destination_address": "123 Security Lane",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 2.0,
        "parcel_type": "SMALL_PARCEL",
        "priority": "EXPRESS",
        "price": 0.01  # Adversarial low price
    }, headers=headers)

    assert resp_arb.status_code == 201
    parcel_arb = resp_arb.json()["data"]
    # Small parcel 2.0kg Express: (45 + 50) * 1.5 = 142.50
    assert Decimal(str(parcel_arb["price"])) == Decimal("142.50")
    assert Decimal(str(parcel_arb["price"])) != Decimal("0.01")


def test_citizen_cannot_patch_price_arbitrarily(client, seed_users, db):
    """
    Security Test: Ensure citizen cannot use PATCH /api/v1/parcels/{id} to modify price directly.
    """
    citizen = seed_users["citizen1"]
    headers = auth_header_for_user(citizen)

    # 1. Book parcel normally
    resp = client.post("/api/v1/parcels", json={
        "receiver_name": "Patch Test Receiver",
        "receiver_phone": "9876543210",
        "destination_address": "123 Security Lane",
        "destination_city": "Chennai",
        "destination_state": "Tamil Nadu",
        "destination_pin": "600001",
        "weight": 1.0,
        "parcel_type": "DOCUMENT",
        "priority": "STANDARD"
    }, headers=headers)
    tracking_id = resp.json()["data"]["tracking_id"]
    initial_price = Decimal(str(resp.json()["data"]["price"]))
    assert initial_price == Decimal("40.00")

    # 2. Citizen attempts PATCH with price=5.00
    patch_resp = client.patch(f"/api/v1/parcels/{tracking_id}", json={
        "price": 5.00,
        "destination_address": "456 Updated Lane"
    }, headers=headers)

    assert patch_resp.status_code == 200
    updated_data = patch_resp.json()["data"]
    assert updated_data["destination_address"] == "456 Updated Lane"
    # Price must remain the authoritative server price (40.00), not 5.00
    assert Decimal(str(updated_data["price"])) == Decimal("40.00")

    # 3. Changing weight from 1.0 to 2.0 via PATCH should recalculate server price: 25 + (2.0*15) = 55.00
    weight_patch = client.patch(f"/api/v1/parcels/{tracking_id}", json={
        "weight": 2.0
    }, headers=headers)
    assert weight_patch.status_code == 200
    assert Decimal(str(weight_patch.json()["data"]["price"])) == Decimal("55.00")
