import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Union

# Name: Unicode letters, spaces, optional periods for initials.
# Accepts: "Rahul Kumar", "Priya Sharma", "A. Kumar", "Mohammed Ali", "K. R. Narayanan"
# Rejects: Digits ("Rahul123"), symbols ("@@Rahul", "Priya_Sharma")
NAME_REGEX = re.compile(
    r"^[A-Za-z\u00C0-\u024F\u0900-\u097F]+(?:\.?\s+[A-Za-z\u00C0-\u024F\u0900-\u097F]+)*\.?$"
)

# Indian Mobile Phone: 10 digits starting with 6, 7, 8, or 9
PHONE_REGEX = re.compile(r"^[6-9]\d{9}$")

# Indian Postal PIN Code: 6 digits starting with 1-9
PIN_REGEX = re.compile(r"^[1-9][0-9]{5}$")

# Address characters allowed: letters, numbers, spaces, commas, periods, hyphens, slashes, hashes, parentheses
ADDRESS_ALLOWED_REGEX = re.compile(r"^[A-Za-z0-9\s,.\-/#()]+$")


def validate_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Name must be a string.")
    
    # Strip whitespace and collapse internal repeated spaces
    cleaned = " ".join(value.strip().split())
    if len(cleaned) < 2:
        raise ValueError("Name must contain at least 2 characters.")
    if len(cleaned) > 100:
        raise ValueError("Name must not exceed 100 characters.")
    
    if not NAME_REGEX.match(cleaned):
        raise ValueError(
            "Name can only contain alphabetic characters, spaces, and optional periods for initials. "
            "Numbers and special symbols (@, #, _, etc.) are not allowed."
        )
    return cleaned


def validate_phone(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Phone number must be a string.")
    
    cleaned = value.strip().replace(" ", "").replace("-", "")
    # Handle optional +91 or leading 0 prefix
    if cleaned.startswith("+91") and len(cleaned) == 13:
        cleaned = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]
    
    if not PHONE_REGEX.match(cleaned):
        raise ValueError("Phone number must be a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.")
    return cleaned


def validate_pin(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("PIN code must be a string.")
    
    cleaned = value.strip()
    if not PIN_REGEX.match(cleaned):
        raise ValueError("PIN code must contain exactly 6 digits and cannot start with 0.")
    return cleaned


def validate_address(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Address must be a string.")
    
    cleaned = " ".join(value.strip().split())
    if len(cleaned) < 10:
        raise ValueError("Address must contain at least 10 characters.")
    if len(cleaned) > 300:
        raise ValueError("Address must not exceed 300 characters.")
    
    if not ADDRESS_ALLOWED_REGEX.match(cleaned):
        raise ValueError("Address contains invalid special characters. Allowed: letters, numbers, spaces, commas, periods, hyphens, slashes.")
    
    # Reject clearly meaningless repetitive or single-character inputs
    # e.g., 'aaaa', '123', '!!!'
    unique_chars = set(cleaned.replace(" ", "").lower())
    if len(unique_chars) < 3:
        raise ValueError("Please enter a meaningful, detailed address.")
    
    # Check that it has at least some alphabetic content
    if not any(c.isalpha() for c in cleaned):
        raise ValueError("Address must contain letters identifying the street/area.")
    
    return cleaned


def validate_weight(value: Union[float, int, Decimal, str]) -> Decimal:
    try:
        dec_val = Decimal(str(value))
    except Exception:
        raise ValueError("Weight must be a valid numeric decimal value.")
    
    if dec_val <= Decimal("0"):
        raise ValueError("Weight must be greater than 0 kg.")
    if dec_val > Decimal("50.00"):
        raise ValueError("Maximum allowed parcel weight for this prototype is 50.00 kg.")
    
    # Round / quantify to max 2 decimal places
    if dec_val.as_tuple().exponent < -2:
        raise ValueError("Weight cannot exceed 2 decimal places.")
    
    return round(dec_val, 2)


def validate_pickup_date(target_date: date) -> date:
    today = date.today()
    if target_date < today:
        raise ValueError("Pickup date cannot be in the past.")
    max_date = today + timedelta(days=14)
    if target_date > max_date:
        raise ValueError(f"Pickup date cannot be more than 14 days in the future (max: {max_date.isoformat()}).")
    return target_date
