from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.enums import ParcelTrackingStatus


class TrackingEventResponse(BaseModel):
    id: int
    parcel_id: int
    previous_status: Optional[str] = None
    new_status: str
    event_type: str
    location_label: str
    description: str
    actor_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrackingTimelineResponse(BaseModel):
    tracking_id: str
    current_status: str
    destination_city: str
    destination_pin: str
    last_updated: datetime
    timeline: List[TrackingEventResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PublicTrackingResponse(BaseModel):
    tracking_id: str
    current_status: str
    sender_masked: str
    receiver_masked: str
    destination_city: str
    destination_pin: str
    last_updated: datetime
    timeline: List[TrackingEventResponse] = []

    model_config = ConfigDict(from_attributes=True)


class QRCodeResponse(BaseModel):
    tracking_id: str
    qr_token: str
    qr_code_base64: str
    payload_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QRResolveRequest(BaseModel):
    qr_token: str

    @field_validator("qr_token")
    @classmethod
    def clean_token(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("QR token cannot be empty.")
        return v.strip()


class TrackingEventCreateRequest(BaseModel):
    new_status: ParcelTrackingStatus
    location_label: str
    description: Optional[str] = None

    @field_validator("location_label")
    @classmethod
    def validate_location(cls, v: str) -> str:
        if not v or len(v.strip()) < 3:
            raise ValueError("Location label must be at least 3 characters long.")
        return v.strip()


class DeliveryOTPResponse(BaseModel):
    tracking_id: str
    expires_at: datetime
    message: str
    test_otp: Optional[str] = None  # Populated only in prototype/testing environments


class DeliveryVerifyRequest(BaseModel):
    otp: str

    @field_validator("otp")
    @classmethod
    def validate_otp_format(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned.isdigit() or len(cleaned) != 6:
            raise ValueError("OTP must be exactly 6 numeric digits.")
        return cleaned


class DeliveryVerifyResponse(BaseModel):
    tracking_id: str
    status: str
    delivered_at: datetime
    verified: bool
