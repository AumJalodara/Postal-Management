import logging
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User
from app.models.parcel import Parcel
from app.models.delivery_agent import DeliveryAgent
from app.models.pickup import PickupRequest
from app.schemas.parcel import ParcelCreate, ParcelUpdate
from app.services.tracking_service import generate_prototype_tracking_id
from app.services.pricing_service import calculate_parcel_price

logger = logging.getLogger(__name__)


def create_parcel(
    db: Session,
    sender_id: int,
    parcel_in: ParcelCreate,
    is_admin_override: bool = False,
    admin_price: Optional[Decimal] = None
) -> Parcel:
    """
    Creates a new parcel and assigns a unique server-generated prototype tracking ID.
    Authoritatively calculates price server-side based on statutory postal tariff schedule.
    Client-provided price in parcel_in is never trusted for normal booking.
    """
    # Authoritatively validate geographic consistency to prevent state-PIN mismatch
    from app.services.postal_location_service import postal_location_service
    loc_check = postal_location_service.validate_location(
        state=parcel_in.destination_state,
        city=parcel_in.destination_city,
        pin=parcel_in.destination_pin
    )
    if not loc_check.get("is_valid", True) and loc_check.get("mismatch_type") == "STATE_MISMATCH":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "ADDRESS_STATE_MISMATCH",
                "message": loc_check.get("message", "Selected state does not match the destination PIN code.")
            }
        )

    tracking_id = generate_prototype_tracking_id(db)
    
    if is_admin_override and admin_price is not None:
        final_price = Decimal(str(admin_price))
        logger.info(f"Admin override applied for parcel price: {final_price}")
    else:
        # Authoritative server-side calculation
        final_price = calculate_parcel_price(
            weight=parcel_in.weight,
            parcel_type=parcel_in.parcel_type,
            priority=parcel_in.priority
        )
    
    parcel = Parcel(
        tracking_id=tracking_id,
        sender_id=sender_id,
        receiver_name=parcel_in.receiver_name,
        receiver_phone=parcel_in.receiver_phone,
        destination_address=parcel_in.destination_address,
        destination_city=parcel_in.destination_city,
        destination_state=parcel_in.destination_state,
        destination_pin=parcel_in.destination_pin,
        weight=parcel_in.weight,
        parcel_type=parcel_in.parcel_type,
        priority=parcel_in.priority,
        price=final_price
    )

    db.add(parcel)
    db.commit()
    db.refresh(parcel)

    # Module 2 Integration: Record initial BOOKED tracking event
    from app.models.tracking import ParcelTrackingEvent
    from app.services.qr_service import get_or_create_parcel_qr

    initial_event = ParcelTrackingEvent(
        parcel_id=parcel.id,
        previous_status=None,
        new_status="BOOKED",
        event_type="BOOKED",
        location_label=f"{parcel.destination_city} (Booking Office)",
        description="Consignment booked successfully by citizen.",
        actor_type="CITIZEN",
        actor_id=sender_id
    )
    db.add(initial_event)
    # Pre-generate secure QR code
    get_or_create_parcel_qr(db, parcel)

    db.commit()
    db.refresh(parcel)

    logger.info(f"Parcel created: ID={parcel.id}, TrackingID={parcel.tracking_id} Price={parcel.price} by Sender={sender_id}")
    return parcel


def get_user_parcels(db: Session, sender_id: int) -> List[Parcel]:
    """Retrieve all parcels booked by the authenticated citizen."""
    return (
        db.query(Parcel)
        .filter(Parcel.sender_id == sender_id)
        .order_by(Parcel.created_at.desc())
        .all()
    )


def get_parcel_by_tracking_id(db: Session, tracking_id: str, current_user: User) -> Parcel:
    """
    Retrieve parcel details with strict ownership / role verification.
    """
    parcel = db.query(Parcel).filter(Parcel.tracking_id == tracking_id).first()
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PARCEL_NOT_FOUND", "message": f"Parcel with tracking ID {tracking_id} not found."}
        )
    
    # Ownership authorization check
    if current_user.role == UserRole.ADMIN:
        return parcel
    
    if parcel.sender_id == current_user.id:
        return parcel
    
    if current_user.role == UserRole.AGENT:
        agent = db.query(DeliveryAgent).filter(DeliveryAgent.user_id == current_user.id).first()
        if agent:
            # Check if assigned to this parcel's pickup
            pickup = db.query(PickupRequest).filter(
                PickupRequest.parcel_id == parcel.id,
                PickupRequest.assigned_agent_id == agent.id
            ).first()
            if pickup:
                return parcel

    # Otherwise deny access
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "ACCESS_DENIED", "message": "You are not authorized to view this parcel's details."}
    )


def update_parcel(
    db: Session,
    parcel: Parcel,
    parcel_update: ParcelUpdate,
    is_admin_override: bool = False
) -> Parcel:
    """
    Updates a parcel's fields.
    If weight, parcel_type, or priority are modified, authoritative tariff is recalculated.
    Client-provided price is stripped unless is_admin_override is True.
    """
    update_data = parcel_update.model_dump(exclude_unset=True)
    
    if not is_admin_override:
        update_data.pop("price", None)
        
    for field, value in update_data.items():
        setattr(parcel, field, value)
        
    # Re-calculate server-side price if specs changed
    if any(k in update_data for k in ("weight", "parcel_type", "priority")) and not is_admin_override:
        parcel.price = calculate_parcel_price(
            weight=parcel.weight,
            parcel_type=parcel.parcel_type,
            priority=parcel.priority
        )
        
    db.commit()
    db.refresh(parcel)
    
    logger.info(f"Parcel {parcel.tracking_id} updated with {update_data}, final price={parcel.price}")
    return parcel
