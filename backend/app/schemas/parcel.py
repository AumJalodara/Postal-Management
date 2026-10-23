from datetime import datetime
from decimal import Decimal
from typing import Union, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.enums import ParcelType, Priority
from app.validation.validators import (
    validate_name,
    validate_phone,
    validate_pin,
    validate_address,
    validate_weight,
)


class ParcelQuoteRequest(BaseModel):
    weight: Union[float, int, Decimal]
    parcel_type: ParcelType
    priority: Priority = Priority.STANDARD

    @field_validator("weight")
    @classmethod
    def check_weight(cls, v: Union[float, int, Decimal]) -> Decimal:
        return validate_weight(v)


class ParcelQuoteResponse(BaseModel):
    weight: float
    parcel_type: str
    priority: str
    base_price: float
    weight_charge: float
    express_surcharge: float
    total_price: float
    currency: str = "INR"
    description: str


class ParcelCreate(BaseModel):
    receiver_name: str
    receiver_phone: str
    destination_address: str
    destination_city: str
    destination_state: str
    destination_pin: str
    weight: Union[float, int, Decimal]
    parcel_type: ParcelType
    priority: Priority = Priority.STANDARD
    price: Optional[Union[float, int, Decimal]] = None

    @field_validator("receiver_name")
    @classmethod
    def check_receiver_name(cls, v: str) -> str:
        return validate_name(v)

    @field_validator("receiver_phone")
    @classmethod
    def check_receiver_phone(cls, v: str) -> str:
        return validate_phone(v)

    @field_validator("destination_address")
    @classmethod
    def check_address(cls, v: str) -> str:
        return validate_address(v)

    @field_validator("destination_city", "destination_state")
    @classmethod
    def check_city_state(cls, v: str) -> str:
        return validate_name(v)

    @field_validator("destination_pin")
    @classmethod
    def check_pin(cls, v: str) -> str:
        return validate_pin(v)

    @field_validator("weight")
    @classmethod
    def check_weight(cls, v: Union[float, int, Decimal]) -> Decimal:
        return validate_weight(v)


class ParcelUpdate(BaseModel):
    receiver_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    destination_address: Optional[str] = None
    destination_city: Optional[str] = None
    destination_state: Optional[str] = None
    destination_pin: Optional[str] = None
    weight: Optional[Union[float, int, Decimal]] = None
    parcel_type: Optional[ParcelType] = None
    priority: Optional[Priority] = None
    price: Optional[Union[float, int, Decimal]] = None

    @field_validator("receiver_name")
    @classmethod
    def check_receiver_name(cls, v: Optional[str]) -> Optional[str]:
        return validate_name(v) if v is not None else v

    @field_validator("receiver_phone")
    @classmethod
    def check_receiver_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone(v) if v is not None else v

    @field_validator("destination_address")
    @classmethod
    def check_address(cls, v: Optional[str]) -> Optional[str]:
        return validate_address(v) if v is not None else v

    @field_validator("destination_city", "destination_state")
    @classmethod
    def check_city_state(cls, v: Optional[str]) -> Optional[str]:
        return validate_name(v) if v is not None else v

    @field_validator("destination_pin")
    @classmethod
    def check_pin(cls, v: Optional[str]) -> Optional[str]:
        return validate_pin(v) if v is not None else v

    @field_validator("weight")
    @classmethod
    def check_weight(cls, v: Optional[Union[float, int, Decimal]]) -> Optional[Decimal]:
        return validate_weight(v) if v is not None else v


class ParcelResponse(BaseModel):
    id: int
    tracking_id: str
    sender_id: int
    receiver_name: str
    receiver_phone: str
    destination_address: str
    destination_city: str
    destination_state: str
    destination_pin: str
    weight: Decimal
    parcel_type: ParcelType
    priority: Priority
    price: Decimal
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

