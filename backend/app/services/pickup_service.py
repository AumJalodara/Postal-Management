import logging
import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.enums import PickupStatus, UserRole
from app.models.user import User
from app.models.parcel import Parcel
from app.models.pickup import PickupRequest, PickupStatusHistory
from app.models.delivery_agent import DeliveryAgent
from app.models.operational_history import OperationalHistory
from app.schemas.pickup import PickupCreate
from app.services.state_machine import transition_pickup_status
from app.services.agent_assignment import assign_pickup_agent

logger = logging.getLogger(__name__)


def create_pickup(
    db: Session,
    requester_id: int,
    pickup_in: PickupCreate,
    idempotency_key: str
) -> PickupRequest:
    """
    Creates a new doorstep pickup request with idempotency protection
    and automatic agent assignment attempt.
    """
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MISSING_IDEMPOTENCY_KEY", "message": "Idempotency-Key header is required."}
        )

    # 1. Check Idempotency: Return existing pickup if same key was already processed
    existing_by_key = (
        db.query(PickupRequest)
        .options(joinedload(PickupRequest.parcel), joinedload(PickupRequest.history))
        .filter(PickupRequest.idempotency_key == idempotency_key.strip())
        .first()
    )
    if existing_by_key:
        logger.info(f"Idempotent pickup request detected for key {idempotency_key}. Returning existing Pickup #{existing_by_key.id}")
        return existing_by_key

    # 2. Verify Parcel existence and ownership
    parcel = db.query(Parcel).filter(Parcel.id == pickup_in.parcel_id).first()
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PARCEL_NOT_FOUND", "message": f"Parcel ID {pickup_in.parcel_id} does not exist."}
        )
    if parcel.sender_id != requester_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN_PARCEL", "message": "You can only request pickup for parcels you booked."}
        )

    # 3. Verify no active pickup exists for this parcel
    active_pickup = (
        db.query(PickupRequest)
        .filter(
            PickupRequest.parcel_id == parcel.id,
            PickupRequest.status != PickupStatus.CANCELLED
        )
        .first()
    )
    if active_pickup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ACTIVE_PICKUP_EXISTS",
                "message": f"Parcel already has an active pickup request (#{active_pickup.id}) in status {active_pickup.status.value}."
            }
        )

    # 4. Create Pickup in PENDING status
    pickup = PickupRequest(
        parcel_id=parcel.id,
        requester_id=requester_id,
        pickup_address=pickup_in.pickup_address,
        pickup_city=pickup_in.pickup_city,
        pickup_state=pickup_in.pickup_state,
        pickup_pin=pickup_in.pickup_pin,
        requested_date=pickup_in.requested_date,
        status=PickupStatus.PENDING,
        idempotency_key=idempotency_key.strip()
    )
    db.add(pickup)
    db.flush()

    # Initial history entry
    initial_history = PickupStatusHistory(
        pickup_id=pickup.id,
        old_status=None,
        new_status=PickupStatus.PENDING.value,
        changed_by=requester_id,
        changed_by_role="CITIZEN",
        reason="Initial pickup request registered"
    )
    op_hist = OperationalHistory(
        event_type="PICKUP_CREATED",
        entity_type="pickup_request",
        entity_id=pickup.id,
        actor_user_id=requester_id,
        agent_id=None,
        previous_status=None,
        new_status=PickupStatus.PENDING.value,
        description="Initial pickup request registered"
    )
    db.add(initial_history)
    db.add(op_hist)
    db.commit()
    db.refresh(pickup)

    logger.info(f"Pickup request created: #{pickup.id} for Parcel #{parcel.id} (Status: PENDING)")

    # 5. Attempt automatic agent assignment
    assign_pickup_agent(db, pickup)

    # Reload with relationships
    return (
        db.query(PickupRequest)
        .options(joinedload(PickupRequest.parcel), joinedload(PickupRequest.history))
        .filter(PickupRequest.id == pickup.id)
        .first()
    )


def get_user_pickups(db: Session, requester_id: int) -> List[PickupRequest]:
    """Retrieve all pickups created by the citizen."""
    return (
        db.query(PickupRequest)
        .options(joinedload(PickupRequest.parcel), joinedload(PickupRequest.history))
        .filter(PickupRequest.requester_id == requester_id)
        .order_by(PickupRequest.created_at.desc())
        .all()
    )


def get_pickup_by_id(db: Session, pickup_id: int, current_user: User) -> PickupRequest:
    """Retrieve a pickup by ID with authorization verification."""
    pickup = (
        db.query(PickupRequest)
        .options(joinedload(PickupRequest.parcel), joinedload(PickupRequest.history))
        .filter(PickupRequest.id == pickup_id)
        .first()
    )
    if not pickup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PICKUP_NOT_FOUND", "message": f"Pickup #{pickup_id} not found."}
        )

    # Check authorization
    if current_user.role == UserRole.ADMIN:
        return pickup
    if current_user.role == UserRole.CITIZEN and pickup.requester_id == current_user.id:
        return pickup
    if current_user.role == UserRole.AGENT:
        agent = db.query(DeliveryAgent).filter(DeliveryAgent.user_id == current_user.id).first()
        if agent and pickup.assigned_agent_id == agent.id:
            return pickup

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "ACCESS_DENIED", "message": "You are not authorized to view this pickup."}
    )


def cancel_pickup(db: Session, pickup_id: int, current_user: User, reason: Optional[str]) -> PickupRequest:
    """Cancel a pickup request if in PENDING or ASSIGNED state."""
    pickup = (
        db.query(PickupRequest)
        .options(joinedload(PickupRequest.parcel), joinedload(PickupRequest.history))
        .filter(PickupRequest.id == pickup_id)
        .first()
    )
    if not pickup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PICKUP_NOT_FOUND", "message": f"Pickup #{pickup_id} not found."}
        )

    # Only requester or admin can cancel
    if current_user.role != UserRole.ADMIN and pickup.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCESS_DENIED", "message": "You cannot cancel another citizen's pickup request."}
        )

    updated_pickup = transition_pickup_status(
        db=db,
        pickup=pickup,
        target_status=PickupStatus.CANCELLED,
        actor_user=current_user,
        reason=reason or "Cancelled by user request"
    )
    return updated_pickup
