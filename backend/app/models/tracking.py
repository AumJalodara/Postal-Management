from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class ParcelTrackingEvent(Base):
    __tablename__ = "parcel_tracking_events"

    id = Column(Integer, primary_key=True, index=True)
    parcel_id = Column(Integer, ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    location_label = Column(String(150), nullable=False)
    description = Column(String(300), nullable=False)
    actor_type = Column(String(50), nullable=False)  # SYSTEM, AGENT, CITIZEN, ADMIN
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    parcel = relationship("Parcel", back_populates="tracking_events")
    actor = relationship("User")


class ParcelQRCode(Base):
    __tablename__ = "parcel_qr_codes"

    id = Column(Integer, primary_key=True, index=True)
    parcel_id = Column(Integer, ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False, index=True)
    qr_token = Column(String(128), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    parcel = relationship("Parcel", back_populates="qr_code")


class DeliveryOTP(Base):
    __tablename__ = "delivery_otps"

    id = Column(Integer, primary_key=True, index=True)
    parcel_id = Column(Integer, ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    parcel = relationship("Parcel", back_populates="delivery_otps")


class PostalLocation(Base):
    """
    Reference schema for Government of India Pincode Directory integration.
    Allows future datasets to be integrated without modifying the core parcel model.
    """
    __tablename__ = "postal_locations"

    id = Column(Integer, primary_key=True, index=True)
    pincode = Column(String(6), nullable=False, index=True)
    office_name = Column(String(150), nullable=False)
    office_type = Column(String(50), nullable=True)
    district = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    region = Column(String(100), nullable=True)
    division = Column(String(100), nullable=True)
    circle = Column(String(100), nullable=True)
    delivery_status = Column(String(50), nullable=True)
    latitude = Column(String(50), nullable=True)
    longitude = Column(String(50), nullable=True)
