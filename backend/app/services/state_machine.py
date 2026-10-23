import logging
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import PickupStatus, UserRole
from app.models.user import User
from app.models.pickup import PickupRequest, PickupStatusHistory
from app.models.delivery_agent import DeliveryAgent
from app.models.operational_history import OperationalHistory

logger = logging.getLogger(__name__)

# Explicitly allowed transitions: (current_status, target_status)
ALLOWED_TRANSITIONS = {
    (PickupStatus.PENDING, PickupStatus.ASSIGNED),
    (PickupStatus.ASSIGNED, PickupStatus.ACCEPTED),
    (PickupStatus.ACCEPTED, PickupStatus.PICKED_UP),
    (PickupStatus.PENDING, PickupStatus.CANCELLED),
    (PickupStatus.ASSIGNED, PickupStatus.CANCELLED),
}


def transition_pickup_status(
    db: Session,
    pickup: PickupRequest,
    target_status: PickupStatus,
    actor_user: Optional[User] = None,
    actor_role: Optional[str] = None,
    reason: Optional[str] = None
) -> PickupRequest:
    """
    Centralized, authoritative state machine transition function.
    Validates state transitions, authorization, atomic history recording,
    and agent workload adjustments within a single database transaction.
    """
    current_status = pickup.status

    # Validate transition rule
    if (current_status, target_status) not in ALLOWED_TRANSITIONS:
        logger.warning(
            f"Invalid transition attempted for Pickup #{pickup.id}: {current_status} -> {target_status}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_STATE_TRANSITION",
                "message": f"Cannot transition pickup from {current_status.value} to {target_status.value}."
            }
        )

    # Validate actor authorization for transition
    effective_role = actor_role or (actor_user.role.value if actor_user else "SYSTEM")
    actor_id = actor_user.id if actor_user else None

    if target_status == PickupStatus.ASSIGNED:
        if effective_role not in ["SYSTEM", UserRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN_TRANSITION", "message": "Only the system or admin can assign agents."}
            )

    elif target_status in [PickupStatus.ACCEPTED, PickupStatus.PICKED_UP]:
        if effective_role != UserRole.AGENT.value and effective_role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN_TRANSITION", "message": "Only an assigned agent can accept or complete pickups."}
            )
        # Verify the agent is actually assigned to this pickup
        if actor_user and effective_role == UserRole.AGENT.value:
            agent = db.query(DeliveryAgent).filter(DeliveryAgent.user_id == actor_user.id).first()
            if not agent or pickup.assigned_agent_id != agent.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "NOT_ASSIGNED_AGENT", "message": "You are not the assigned delivery agent for this pickup."}
                )

    elif target_status == PickupStatus.CANCELLED:
        if effective_role != UserRole.CITIZEN.value and effective_role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN_TRANSITION", "message": "Only the requesting citizen can cancel this pickup."}
            )
        # Verify ownership
        if actor_user and effective_role == UserRole.CITIZEN.value:
            if pickup.requester_id != actor_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "NOT_PICKUP_OWNER", "message": "You cannot cancel another citizen's pickup request."}
                )

    # Workload adjustment
    # When completed or cancelled, decrement active pickup count of assigned agent
    if target_status in [PickupStatus.PICKED_UP, PickupStatus.CANCELLED]:
        if pickup.assigned_agent_id:
            agent = db.query(DeliveryAgent).filter(DeliveryAgent.id == pickup.assigned_agent_id).first()
            if agent and agent.active_pickup_count > 0:
                agent.active_pickup_count -= 1

    # Record history
    history = PickupStatusHistory(
        pickup_id=pickup.id,
        old_status=current_status.value,
        new_status=target_status.value,
        changed_by=actor_id,
        changed_by_role=effective_role,
        reason=reason or f"Transitioned to {target_status.value}"
    )

    # Update pickup state
    pickup.status = target_status
    db.add(history)
    
    op_event = "PICKUP_STATUS_CHANGED"
    if target_status == PickupStatus.ACCEPTED:
        op_event = "PICKUP_ACCEPTED"
    elif target_status == PickupStatus.PICKED_UP:
        op_event = "PICKUP_COMPLETED"
        
    op_hist = OperationalHistory(
        event_type=op_event,
        entity_type="pickup_request",
        entity_id=pickup.id,
        actor_user_id=actor_id,
        agent_id=pickup.assigned_agent_id,
        previous_status=current_status.value,
        new_status=target_status.value,
        description=reason or f"Transitioned to {target_status.value}"
    )
    db.add(op_hist)
    db.add(pickup)

    # Module 2 Integration: Advance parcel tracking when doorstep pickup completes
    if target_status == PickupStatus.PICKED_UP and pickup.parcel:
        from app.models.tracking import ParcelTrackingEvent
        from app.services.qr_service import get_or_create_parcel_qr

        prev_status = pickup.parcel.status or "BOOKED"
        pickup.parcel.status = "PICKED_UP"
        tracking_event = ParcelTrackingEvent(
            parcel_id=pickup.parcel.id,
            previous_status=prev_status,
            new_status="PICKED_UP",
            event_type="PICKED_UP",
            location_label=f"Pincode {pickup.pickup_pin}",
            description="Consignment collected from sender doorstep.",
            actor_type=effective_role,
            actor_id=actor_id
        )
        db.add(pickup.parcel)
        db.add(tracking_event)
        # Ensure QR code is initialized
        get_or_create_parcel_qr(db, pickup.parcel)

    db.commit()
    db.refresh(pickup)

    logger.info(
        f"Pickup #{pickup.id} transitioned from {current_status.value} to {target_status.value} by {effective_role}"
    )
    return pickup
