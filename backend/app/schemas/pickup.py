from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.enums import PickupStatus
from app.schemas.parcel import ParcelResponse
from app.validation.validators import (
    validate_name,
    validate_pin,
    validate_address,
    validate_pickup_date,
)


class PickupCreate(BaseModel):
    parcel_id: int
    pickup_address: str
    pickup_city: str
    pickup_state: str
    pickup_pin: str
    requested_date: date
    idempotency_key: Optional[str] = None

    @field_validator("pickup_address")
    @classmethod
    def check_address(cls, v: str) -> str:
        return validate_address(v)

    @field_validator("pickup_city", "pickup_state")
    @classmethod
    def check_city_state(cls, v: str) -> str:
        return validate_name(v)

    @field_validator("pickup_pin")
    @classmethod
    def check_pin(cls, v: str) -> str:
        return validate_pin(v)

    @field_validator("requested_date")
    @classmethod
    def check_date(cls, v: date) -> date:
        return validate_pickup_date(v)


class PickupHistoryResponse(BaseModel):
    id: int
    pickup_id: int
    old_status: Optional[str] = None
    new_status: str
    changed_by: Optional[int] = None
    changed_by_role: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PickupResponse(BaseModel):
    id: int
    parcel_id: int
    requester_id: int
    pickup_address: str
    pickup_city: str
    pickup_state: str
    pickup_pin: str
    requested_date: date
    assigned_agent_id: Optional[int] = None
    status: PickupStatus
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    parcel: Optional[ParcelResponse] = None
    history: List[PickupHistoryResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PickupCancelRequest(BaseModel):
    reason: Optional[str] = "Cancelled by citizen"
