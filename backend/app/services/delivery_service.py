import logging
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.parcel import Parcel
from app.models.user import User
from app.models.enums import ParcelTrackingStatus, UserRole
from app.models.delivery_agent import DeliveryAgent
from app.models.pickup import PickupRequest
from app.services.otp_service import verify_delivery_otp
from app.services.tracking_state_machine import transition_parcel_tracking
from app.schemas.tracking import DeliveryVerifyResponse

logger = logging.getLogger(__name__)


def is_agent_authorized_for_pin(agent_service_area: str, target_pin: str) -> bool:
    """
    Checks if an agent is authorized for a postal pincode.
    1. Exact 6-digit PIN match.
    2. 2-digit Indian Postal Circle match (e.g. '38' covers Gujarat circle: Ahmedabad, Gandhinagar, etc.).
    """
    if not agent_service_area or not target_pin:
        return False
    a_pin = str(agent_service_area).strip()
    t_pin = str(target_pin).strip()
    if a_pin == t_pin:
        return True
    if len(a_pin) >= 2 and len(t_pin) >= 2 and a_pin[:2] == t_pin[:2]:
        return True
    return False


def verify_agent_parcel_authorization(db: Session, parcel: Parcel, agent_user: User) -> DeliveryAgent:
    """Verifies that the delivery agent is authorized to handle this parcel."""
    if agent_user.role == UserRole.ADMIN:
        agent = db.query(DeliveryAgent).first()
        return agent

    agent = db.query(DeliveryAgent).filter(DeliveryAgent.user_id == agent_user.id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AGENT_PROFILE_NOT_FOUND", "message": "Delivery agent profile not found."}
        )

    # Check if assigned to this parcel's pickup or in delivery service area
    pickup = db.query(PickupRequest).filter(PickupRequest.parcel_id == parcel.id).first()
    is_pickup_agent = bool(pickup and pickup.assigned_agent_id == agent.id)
    is_delivery_agent = is_agent_authorized_for_pin(agent.service_area, parcel.destination_pin)

    if not is_pickup_agent and not is_delivery_agent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCESS_DENIED", "message": "You are not authorized to deliver this consignment outside your service area."}
        )

    return agent



def process_secure_delivery(
    db: Session,
    parcel: Parcel,
    otp: str,
    agent_user: User
) -> DeliveryVerifyResponse:
    """
    Atomic execution of OTP verification and parcel delivery state transition.
    1. Verifies agent authorization.
    2. Verifies OTP and burns it.
    3. Transitions status OUT_FOR_DELIVERY -> DELIVERED.
    4. Creates immutable tracking event.
    5. Commits atomically.
    """
    if parcel.status == ParcelTrackingStatus.DELIVERED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PARCEL_ALREADY_DELIVERED", "message": "Consignment has already been delivered."}
        )

    if parcel.status != ParcelTrackingStatus.OUT_FOR_DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "DELIVERY_NOT_ALLOWED",
                "message": f"Parcel is not out for delivery (Current: {parcel.status})."
            }
        )

    # Verify agent authorization
    agent = verify_agent_parcel_authorization(db, parcel, agent_user)

    # Verify and burn OTP
    verified_otp_record = verify_delivery_otp(db, parcel, otp)

    # Transition tracking state machine
    delivered_event = transition_parcel_tracking(
        db=db,
        parcel=parcel,
        target_status=ParcelTrackingStatus.DELIVERED,
        location_label=f"{parcel.destination_city} (PIN {parcel.destination_pin})",
        description=f"Consignment successfully delivered to {parcel.receiver_name} after OTP verification.",
        actor_user=agent_user,
        is_otp_verified=True
    )

    logger.info(f"Consignment {parcel.tracking_id} successfully delivered by Agent #{agent.id}")

    return DeliveryVerifyResponse(
        tracking_id=parcel.tracking_id,
        status=parcel.status,
        delivered_at=delivered_event.created_at,
        verified=True
    )
