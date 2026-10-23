import pytest
from datetime import date, timedelta
from app.validation.validators import (
    validate_name,
    validate_phone,
    validate_pin,
    validate_weight,
    validate_address,
    validate_pickup_date,
)


# --- Name Validation Tests ---
def test_name_valid():
    assert validate_name("Rahul Kumar") == "Rahul Kumar"
    assert validate_name("Priya Sharma") == "Priya Sharma"
    assert validate_name("A. Kumar") == "A. Kumar"
    assert validate_name("Mohammed Ali") == "Mohammed Ali"
    # Unicode Indian name
    assert validate_name("रवि कुमार") == "रवि कुमार"


def test_name_invalid():
    with pytest.raises(ValueError):
        validate_name("Rahul123")
    with pytest.raises(ValueError):
        validate_name("12345")
    with pytest.raises(ValueError):
        validate_name("@@@")
    with pytest.raises(ValueError):
        validate_name("Priya_Sharma")
    with pytest.raises(ValueError):
        validate_name("R")  # less than 2 chars


# --- Phone Number Validation Tests ---
def test_phone_valid():
    assert validate_phone("9876543210") == "9876543210"
    assert validate_phone("7012345678") == "7012345678"
    assert validate_phone("+919876543210") == "9876543210"  # Normalized prefix
    assert validate_phone("09876543210") == "9876543210"    # Normalized 0


def test_phone_invalid():
    with pytest.raises(ValueError):
        validate_phone("98765")
    with pytest.raises(ValueError):
        validate_phone("98765432101")
    with pytest.raises(ValueError):
        validate_phone("abcdefghij")
    with pytest.raises(ValueError):
        validate_phone("98765abc10")
    with pytest.raises(ValueError):
        validate_phone("5876543210")  # does not start with 6-9


# --- PIN Code Validation Tests ---
def test_pin_valid():
    assert validate_pin("600001") == "600001"
    assert validate_pin("110001") == "110001"
    assert validate_pin("400001") == "400001"


def test_pin_invalid():
    with pytest.raises(ValueError):
        validate_pin("60001")
    with pytest.raises(ValueError):
        validate_pin("6000012")
    with pytest.raises(ValueError):
        validate_pin("ABC123")
    with pytest.raises(ValueError):
        validate_pin("60000A")
    with pytest.raises(ValueError):
        validate_pin("010001")  # cannot start with 0


# --- Weight Validation Tests ---
def test_weight_valid():
    assert float(validate_weight(1)) == 1.0
    assert float(validate_weight(2.5)) == 2.5
    assert float(validate_weight("0.5")) == 0.5
    assert float(validate_weight(10)) == 10.0


def test_weight_invalid():
    with pytest.raises(ValueError):
        validate_weight(0)
    with pytest.raises(ValueError):
        validate_weight(-1)
    with pytest.raises(ValueError):
        validate_weight(-2.5)
    with pytest.raises(ValueError):
        validate_weight("abc")
    with pytest.raises(ValueError):
        validate_weight(55.0)  # Exceeds max 50 kg


# --- Address Validation Tests ---
def test_address_valid():
    addr = "12/4 Gandhi Street, Near Bus Stand"
    assert validate_address(addr) == addr


def test_address_invalid():
    with pytest.raises(ValueError):
        validate_address("aaaa")
    with pytest.raises(ValueError):
        validate_address("123")
    with pytest.raises(ValueError):
        validate_address("!!!")
    with pytest.raises(ValueError):
        validate_address("Short")


# --- Pickup Date Validation Tests ---
def test_pickup_date():
    today = date.today()
    assert validate_pickup_date(today) == today
    assert validate_pickup_date(today + timedelta(days=5)) == today + timedelta(days=5)

    with pytest.raises(ValueError):
        validate_pickup_date(today - timedelta(days=1))  # Past date

    with pytest.raises(ValueError):
        validate_pickup_date(today + timedelta(days=20))  # Exceeds 14 days
