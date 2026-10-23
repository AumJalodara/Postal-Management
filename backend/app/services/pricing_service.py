"""
Postal Pricing Service.

Authoritative server-side tariff calculation based on postal schedule guidelines.
Citizens cannot specify or tamper with parcel prices.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Union
from app.models.enums import ParcelType, Priority


# Base rates and per-kg incremental rates in INR
TARIFF_RATES: Dict[ParcelType, Dict[str, Decimal]] = {
    ParcelType.DOCUMENT: {
        "base_price": Decimal("25.00"),
        "per_kg_rate": Decimal("15.00"),
        "min_weight_kg": Decimal("0.10"),
    },
    ParcelType.SMALL_PARCEL: {
        "base_price": Decimal("45.00"),
        "per_kg_rate": Decimal("25.00"),
        "min_weight_kg": Decimal("0.50"),
    },
    ParcelType.MEDIUM_PARCEL: {
        "base_price": Decimal("90.00"),
        "per_kg_rate": Decimal("35.00"),
        "min_weight_kg": Decimal("2.00"),
    },
    ParcelType.LARGE_PARCEL: {
        "base_price": Decimal("180.00"),
        "per_kg_rate": Decimal("45.00"),
        "min_weight_kg": Decimal("10.00"),
    },
}

PRIORITY_MULTIPLIER: Dict[Priority, Decimal] = {
    Priority.STANDARD: Decimal("1.00"),
    Priority.EXPRESS: Decimal("1.50"),
}


def calculate_parcel_price(
    weight: Union[float, int, Decimal],
    parcel_type: ParcelType,
    priority: Priority = Priority.STANDARD
) -> Decimal:
    """
    Authoritatively computes the final postal tariff.
    Formula: (Base Rate + (Weight * Per-KG Rate)) * Priority Multiplier
    """
    weight_dec = Decimal(str(weight))
    if weight_dec <= Decimal("0.00"):
        weight_dec = Decimal("0.01")

    tariff = TARIFF_RATES.get(parcel_type, TARIFF_RATES[ParcelType.SMALL_PARCEL])
    base_price = tariff["base_price"]
    per_kg = tariff["per_kg_rate"]

    weight_charge = (weight_dec * per_kg)
    subtotal = base_price + weight_charge

    multiplier = PRIORITY_MULTIPLIER.get(priority, Decimal("1.00"))
    total = (subtotal * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return total


def get_price_quote(
    weight: Union[float, int, Decimal],
    parcel_type: ParcelType,
    priority: Priority = Priority.STANDARD
) -> Dict[str, Any]:
    """
    Returns an itemized price quotation breakdown for client display.
    """
    weight_dec = Decimal(str(weight))
    if weight_dec <= Decimal("0.00"):
        weight_dec = Decimal("0.01")

    tariff = TARIFF_RATES.get(parcel_type, TARIFF_RATES[ParcelType.SMALL_PARCEL])
    base_price = tariff["base_price"]
    per_kg = tariff["per_kg_rate"]

    weight_charge = (weight_dec * per_kg).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    subtotal = (base_price + weight_charge).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    multiplier = PRIORITY_MULTIPLIER.get(priority, Decimal("1.00"))
    express_surcharge = Decimal("0.00")
    if priority == Priority.EXPRESS:
        express_surcharge = (subtotal * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    total_price = (subtotal * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "weight": float(weight_dec),
        "parcel_type": parcel_type.value if hasattr(parcel_type, "value") else str(parcel_type),
        "priority": priority.value if hasattr(priority, "value") else str(priority),
        "base_price": float(base_price),
        "weight_charge": float(weight_charge),
        "express_surcharge": float(express_surcharge),
        "total_price": float(total_price),
        "currency": "INR",
        "description": f"Official tariff for {parcel_type.value if hasattr(parcel_type, 'value') else str(parcel_type)} ({weight_dec} kg, {priority.value if hasattr(priority, 'value') else str(priority)})"
    }
