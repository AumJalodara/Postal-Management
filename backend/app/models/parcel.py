from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, CheckConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.enums import ParcelType, Priority, ParcelTrackingStatus


def utc_now():
    return datetime.now(timezone.utc)


class Parcel(Base):
    __tablename__ = "parcels"
    __table_args__ = (
        CheckConstraint("weight > 0 AND weight <= 50", name="check_parcel_weight_range"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(String(30), unique=True, index=True, nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    receiver_name = Column(String(100), nullable=False)
    receiver_phone = Column(String(15), nullable=False)
    destination_address = Column(String(300), nullable=False)
    destination_city = Column(String(100), nullable=False)
    destination_state = Column(String(100), nullable=False)
    destination_pin = Column(String(6), nullable=False, index=True)
    weight = Column(Numeric(6, 2), nullable=False)
    parcel_type = Column(SQLEnum(ParcelType), nullable=False)
    priority = Column(SQLEnum(Priority), default=Priority.STANDARD, nullable=False)
    price = Column(Numeric(10, 2), nullable=False, default=0.00)
    status = Column(String(50), default=ParcelTrackingStatus.BOOKED.value, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    sender = relationship("User", back_populates="parcels")
    pickup_request = relationship("PickupRequest", back_populates="parcel", uselist=False, cascade="all, delete-orphan")
    tracking_events = relationship("ParcelTrackingEvent", back_populates="parcel", cascade="all, delete-orphan", order_by="ParcelTrackingEvent.created_at")
    qr_code = relationship("ParcelQRCode", back_populates="parcel", uselist=False, cascade="all, delete-orphan")
    delivery_otps = relationship("DeliveryOTP", back_populates="parcel", cascade="all, delete-orphan", order_by="DeliveryOTP.id.desc()")
