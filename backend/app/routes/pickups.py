from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.pickup import PickupCreate, PickupResponse, PickupCancelRequest
from app.schemas.common import ApiResponse
from app.auth.dependencies import get_current_user, require_roles
from app.services.pickup_service import (
    create_pickup,
    get_user_pickups,
    get_pickup_by_id,
    cancel_pickup,
)

router = APIRouter(prefix="/pickups", tags=["Doorstep Pickups"])


@router.post("", response_model=ApiResponse[PickupResponse], status_code=status.HTTP_201_CREATED)
def request_pickup(
    pickup_in: PickupCreate,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(require_roles(UserRole.CITIZEN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Create a doorstep pickup request for a booked parcel.
    Requires an Idempotency-Key header (or body field) to guarantee safe retries.
    Automatically assigns an eligible delivery agent if available.
    """
    key = idempotency_key_header or pickup_in.idempotency_key
    if not key or not key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MISSING_IDEMPOTENCY_KEY", "message": "Idempotency-Key header is required."}
        )

    pickup = create_pickup(
        db=db,
        requester_id=current_user.id,
        pickup_in=pickup_in,
        idempotency_key=key.strip()
    )
    return ApiResponse.ok(data=PickupResponse.model_validate(pickup))


@router.get("/my", response_model=ApiResponse[List[PickupResponse]])
def list_my_pickups(
    current_user: User = Depends(require_roles(UserRole.CITIZEN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """List all pickup requests requested by the authenticated citizen."""
    pickups = get_user_pickups(db=db, requester_id=current_user.id)
    return ApiResponse.ok(data=[PickupResponse.model_validate(p) for p in pickups])


@router.get("/{pickup_id}", response_model=ApiResponse[PickupResponse])
def get_pickup(
    pickup_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve details and audit history for a single pickup request."""
    pickup = get_pickup_by_id(db=db, pickup_id=pickup_id, current_user=current_user)
    return ApiResponse.ok(data=PickupResponse.model_validate(pickup))


@router.post("/{pickup_id}/cancel", response_model=ApiResponse[PickupResponse])
def cancel_my_pickup(
    pickup_id: int,
    cancel_in: Optional[PickupCancelRequest] = None,
    current_user: User = Depends(require_roles(UserRole.CITIZEN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Cancel a pending or assigned pickup request."""
    reason = cancel_in.reason if cancel_in else "Cancelled by citizen request"
    pickup = cancel_pickup(db=db, pickup_id=pickup_id, current_user=current_user, reason=reason)
    return ApiResponse.ok(data=PickupResponse.model_validate(pickup))
