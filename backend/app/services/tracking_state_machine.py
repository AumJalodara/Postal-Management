import logging
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import ParcelTrackingStatus, UserRole
from app.models.user import User
from app.models.parcel import Parcel
from app.models.tracking import ParcelTrackingEvent

logger = logging.getLogger(__name__)

# Centrally defined valid parcel tracking transitions: (current_status, target_status)
ALLOWED_TRACKING_TRANSITIONS = {
    (ParcelTrackingStatus.BOOKED, ParcelTrackingStatus.PICKED_UP),
    (ParcelTrackingStatus.PICKED_UP, ParcelTrackingStatus.IN_TRANSIT),
    (ParcelTrackingStatus.IN_TRANSIT, ParcelTrackingStatus.ARRIVED_AT_HUB),
    (ParcelTrackingStatus.ARRIVED_AT_HUB, ParcelTrackingStatus.OUT_FOR_DELIVERY),
    (ParcelTrackingStatus.OUT_FOR_DELIVERY, ParcelTrackingStatus.DELIVERY_ATTEMPTED),
    (ParcelTrackingStatus.DELIVERY_ATTEMPTED, ParcelTrackingStatus.OUT_FOR_DELIVERY),
    (ParcelTrackingStatus.OUT_FOR_DELIVERY, ParcelTrackingStatus.DELIVERED),
}


def transition_parcel_tracking(
    db: Session,
    parcel: Parcel,
    target_status: ParcelTrackingStatus,
    location_label: str,
    description: Optional[str] = None,
    actor_user: Optional[User] = None,
    actor_type_override: Optional[str] = None,
    is_otp_verified: bool = False
) -> ParcelTrackingEvent:
    """
    Authoritative, centralized parcel tracking state machine.
    Validates state transitions, enforces delivery via OTP only,
    mutates parcel status, and atomically records immutable tracking event.
    """
    try:
        current_status = ParcelTrackingStatus(parcel.status)
    except ValueError:
        current_status = ParcelTrackingStatus.BOOKED

    # 1. State machine validation
    if (current_status, target_status) not in ALLOWED_TRACKING_TRANSITIONS:
        logger.warning(
            f"Invalid tracking transition attempted for Parcel {parcel.tracking_id}: {current_status.value} -> {target_status.value}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_TRACKING_TRANSITION",
                "message": f"Cannot transition parcel from {current_status.value} to {target_status.value}."
            }
        )

    # 2. Strict Delivery enforcement: DELIVERED requires OTP verification
    if target_status == ParcelTrackingStatus.DELIVERED and not is_otp_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "DELIVERY_NOT_ALLOWED",
                "message": "Direct delivery transition is prohibited. Secure delivery requires OTP verification."
            }
        )

    # Determine actor classification
    if actor_type_override:
        actor_type = actor_type_override
        actor_id = actor_user.id if actor_user else None
    elif actor_user:
        actor_type = actor_user.role.value
        actor_id = actor_user.id
    else:
        actor_type = "SYSTEM"
        actor_id = None

    # Default description based on transition if not supplied
    if not description:
        descriptions = {
            ParcelTrackingStatus.PICKED_UP: "Consignment collected from sender doorstep.",
            ParcelTrackingStatus.IN_TRANSIT: "Consignment in transit between facilities.",
            ParcelTrackingStatus.ARRIVED_AT_HUB: f"Consignment arrived at sorting hub ({location_label}).",
            ParcelTrackingStatus.OUT_FOR_DELIVERY: f"Consignment out for delivery in {location_label}.",
            ParcelTrackingStatus.DELIVERY_ATTEMPTED: "Delivery attempted; recipient unavailable or premises closed.",
            ParcelTrackingStatus.DELIVERED: "Consignment successfully delivered to recipient after OTP verification.",
        }
        description = descriptions.get(target_status, f"Status updated to {target_status.value}.")

    # Atomic state mutation and append-only event insertion
    parcel.status = target_status.value
    event = ParcelTrackingEvent(
        parcel_id=parcel.id,
        previous_status=current_status.value,
        new_status=target_status.value,
        event_type=target_status.value,
        location_label=location_label,
        description=description,
        actor_type=actor_type,
        actor_id=actor_id
    )

    db.add(parcel)
    db.add(event)
    db.commit()
    db.refresh(parcel)
    db.refresh(event)

    logger.info(
        f"Parcel {parcel.tracking_id} tracking updated: {current_status.value} -> {target_status.value} ({location_label}) by {actor_type}"
    )
    return event
