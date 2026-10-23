from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.enums import PickupStatus


def utc_now():
    return datetime.now(timezone.utc)


class PickupRequest(Base):
    __tablename__ = "pickup_requests"

    id = Column(Integer, primary_key=True, index=True)
    parcel_id = Column(Integer, ForeignKey("parcels.id", ondelete="CASCADE"), index=True, nullable=False)
    requester_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    pickup_address = Column(String(300), nullable=False)
    pickup_city = Column(String(100), nullable=False)
    pickup_state = Column(String(100), nullable=False)
    pickup_pin = Column(String(6), nullable=False, index=True)
    requested_date = Column(Date, nullable=False)
    assigned_agent_id = Column(Integer, ForeignKey("delivery_agents.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(SQLEnum(PickupStatus), default=PickupStatus.PENDING, nullable=False, index=True)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    parcel = relationship("Parcel", back_populates="pickup_request")
    requester = relationship("User", back_populates="pickup_requests")
    assigned_agent = relationship("DeliveryAgent", back_populates="assigned_pickups")
    history = relationship("PickupStatusHistory", back_populates="pickup", cascade="all, delete-orphan", order_by="PickupStatusHistory.created_at")


class PickupStatusHistory(Base):
    __tablename__ = "pickup_status_history"

    id = Column(Integer, primary_key=True, index=True)
    pickup_id = Column(Integer, ForeignKey("pickup_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_by_role = Column(String(50), nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    pickup = relationship("PickupRequest", back_populates="history")
    actor = relationship("User")
