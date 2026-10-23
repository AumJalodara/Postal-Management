from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.models.user import User
from app.models.delivery_agent import DeliveryAgent
from app.models.pickup import PickupRequest
from app.models.enums import PickupStatus
from app.schemas.pickup import PickupResponse
from app.schemas.agent import PickupTransitionRequest
from app.schemas.tracking import TrackingEventCreateRequest
from app.schemas.common import ApiResponse
from app.auth.dependencies import get_current_user, get_current_agent
from app.services.state_machine import transition_pickup_status

router = APIRouter(prefix="/agent", tags=["Delivery Agent Operations"])


@router.get("/pickups", response_model=ApiResponse[List[PickupResponse]])
def get_assigned_pickups(
    current_agent: DeliveryAgent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """
    List all doorstep pickups assigned to the authenticated delivery agent.
    Agents can only see pickups assigned to their own profile.
    """
    pickups = (
        db.query(PickupRequest)
        .options(joinedload(PickupRequest.parcel), joinedload(PickupRequest.history))
        .filter(PickupRequest.assigned_agent_id == current_agent.id)
        .order_by(PickupRequest.updated_at.desc())
        .all()
    )
    return ApiResponse.ok(data=[PickupResponse.model_validate(p) for p in pickups])


@router.post("/pickups/{pickup_id}/accept", response_model=ApiResponse[PickupResponse])
def accept_pickup(
    pickup_id: int,
    body: Optional[PickupTransitionRequest] = None,
    current_user: User = Depends(get_current_user),
    current_agent: DeliveryAgent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """
    Agent accepts an assigned pickup.
    State Transition: ASSIGNED -> ACCEPTED.
    """
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

    reason = body.reason if body and body.reason else "Pickup accepted by delivery agent"
    updated = transition_pickup_status(
        db=db,
        pickup=pickup,
        target_status=PickupStatus.ACCEPTED,
        actor_user=current_user,
        reason=reason
    )
    return ApiResponse.ok(data=PickupResponse.model_validate(updated))


@router.post("/pickups/{pickup_id}/complete", response_model=ApiResponse[PickupResponse])
def complete_pickup(
    pickup_id: int,
    body: Optional[PickupTransitionRequest] = None,
    current_user: User = Depends(get_current_user),
    current_agent: DeliveryAgent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """
    Agent marks the pickup as completed (PICKED_UP).
    State Transition: ACCEPTED -> PICKED_UP.
    Automatically decrements agent active pickup workload.
    """
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

    reason = body.reason if body and body.reason else "Parcel physically picked up from doorstep"
    updated = transition_pickup_status(
        db=db,
        pickup=pickup,
        target_status=PickupStatus.PICKED_UP,
        actor_user=current_user,
        reason=reason
    )
    return ApiResponse.ok(data=PickupResponse.model_validate(updated))


@router.get("/deliveries", response_model=ApiResponse[List[dict]])
def get_delivery_queue(
    current_agent: DeliveryAgent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """
    List parcels available in the delivery agent's service area or assigned pickup queue.
    """
    from app.models.parcel import Parcel
    from sqlalchemy import or_, and_

    assigned_pickup_parcel_ids = [
        p[0] for p in db.query(PickupRequest.parcel_id).filter(
            PickupRequest.assigned_agent_id == current_agent.id
        ).all()
    ]

    pin_prefix = current_agent.service_area[:2] if len(current_agent.service_area or "") >= 2 else current_agent.service_area

    parcels = (
        db.query(Parcel)
        .filter(
            Parcel.status.in_(["ARRIVED_AT_HUB", "OUT_FOR_DELIVERY", "DELIVERY_ATTEMPTED", "IN_TRANSIT", "PICKED_UP"]),
            or_(
                Parcel.destination_pin == current_agent.service_area,
                Parcel.destination_pin.startswith(pin_prefix),
                and_(
                    Parcel.id.in_(assigned_pickup_parcel_ids) if assigned_pickup_parcel_ids else False,
                    Parcel.status.in_(["PICKED_UP", "IN_TRANSIT"])
                )
            )
        )
        .order_by(Parcel.updated_at.desc())
        .all()
    )
    result = [
        {
            "id": p.id,
            "tracking_id": p.tracking_id,
            "receiver_name": p.receiver_name,
            "receiver_phone": p.receiver_phone,
            "destination_address": p.destination_address,
            "destination_city": p.destination_city,
            "destination_pin": p.destination_pin,
            "status": p.status,
            "weight": p.weight,
            "priority": p.priority.value if hasattr(p.priority, "value") else p.priority,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        }
        for p in parcels
    ]
    return ApiResponse.ok(data=result)


@router.post("/parcels/{tracking_id}/events")
def update_parcel_status_agent(
    tracking_id: str,
    body: TrackingEventCreateRequest,
    current_user: User = Depends(get_current_user),
    current_agent: DeliveryAgent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """
    Agent route to advance parcel tracking status.
    Requires validated request body and verifies agent service-area authorization.
    """
    from app.models.parcel import Parcel
    from app.models.enums import ParcelTrackingStatus
    from app.services.tracking_state_machine import transition_parcel_tracking

    parcel = db.query(Parcel).filter(Parcel.tracking_id == tracking_id.strip()).first()
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PARCEL_NOT_FOUND", "message": f"Parcel {tracking_id} not found."}
        )

    target_status = body.new_status

    if target_status == ParcelTrackingStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "DELIVERY_NOT_ALLOWED", "message": "Cannot mark as DELIVERED without OTP verification."}
        )

    # For delivery dispatch, verify agent belongs to destination service area
    if target_status in [ParcelTrackingStatus.OUT_FOR_DELIVERY, ParcelTrackingStatus.DELIVERY_ATTEMPTED]:
        from app.services.delivery_service import is_agent_authorized_for_pin
        if not is_agent_authorized_for_pin(current_agent.service_area, parcel.destination_pin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ACCESS_DENIED", "message": "You are not authorized to dispatch deliveries outside your assigned service area."}
            )

    location_label = body.location_label or f"{parcel.destination_city} Facility"
    description = body.description

    event = transition_parcel_tracking(
        db=db,
        parcel=parcel,
        target_status=target_status,
        location_label=location_label,
        description=description,
        actor_user=current_user
    )

    return ApiResponse.ok(data={
        "tracking_id": parcel.tracking_id,
        "new_status": parcel.status,
        "location_label": event.location_label,
        "timestamp": event.created_at.isoformat()
    })


