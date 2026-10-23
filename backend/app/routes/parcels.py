from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.parcel import (
    ParcelCreate,
    ParcelUpdate,
    ParcelResponse,
    ParcelQuoteRequest,
    ParcelQuoteResponse
)
from app.schemas.common import ApiResponse
from app.auth.dependencies import get_current_user, require_roles
from app.services.parcel_service import (
    create_parcel,
    get_user_parcels,
    get_parcel_by_tracking_id,
    update_parcel
)
from app.services.pricing_service import get_price_quote

router = APIRouter(prefix="/parcels", tags=["Parcels"])


@router.post("/quote", response_model=ApiResponse[ParcelQuoteResponse])
def quote_parcel_tariff(
    quote_in: ParcelQuoteRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate an authoritative postal tariff quotation server-side.
    Provides complete itemized breakdown based on official weight and service schedules.
    """
    quote_data = get_price_quote(
        weight=quote_in.weight,
        parcel_type=quote_in.parcel_type,
        priority=quote_in.priority
    )
    return ApiResponse.ok(data=ParcelQuoteResponse.model_validate(quote_data))


@router.post("", response_model=ApiResponse[ParcelResponse], status_code=status.HTTP_201_CREATED)
def book_parcel(
    parcel_in: ParcelCreate,
    current_user: User = Depends(require_roles(UserRole.CITIZEN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Book a new parcel.
    Derives sender identity directly from authenticated citizen's JWT.
    Server authoritatively calculates tariff using statutory pricing rules.
    Client-specified price is never trusted for standard citizen bookings.
    Server generates prototype tracking ID (e.g. GPM-2026-000001).
    """
    is_admin = current_user.role == UserRole.ADMIN
    parcel = create_parcel(
        db=db,
        sender_id=current_user.id,
        parcel_in=parcel_in,
        is_admin_override=False  # Standard citizen booking always uses server-side calculated pricing
    )
    return ApiResponse.ok(data=ParcelResponse.model_validate(parcel))


@router.get("/my", response_model=ApiResponse[List[ParcelResponse]])
def list_my_parcels(
    current_user: User = Depends(require_roles(UserRole.CITIZEN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Retrieve all parcels booked by the authenticated citizen."""
    parcels = get_user_parcels(db=db, sender_id=current_user.id)
    return ApiResponse.ok(data=[ParcelResponse.model_validate(p) for p in parcels])


@router.get("/{tracking_id}", response_model=ApiResponse[ParcelResponse])
def get_parcel(
    tracking_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve parcel by prototype tracking ID.
    Strictly enforces ownership or assigned delivery agent privileges.
    """
    parcel = get_parcel_by_tracking_id(db=db, tracking_id=tracking_id, current_user=current_user)
    return ApiResponse.ok(data=ParcelResponse.model_validate(parcel))


@router.patch("/{tracking_id}", response_model=ApiResponse[ParcelResponse])
def patch_parcel(
    tracking_id: str,
    parcel_in: ParcelUpdate,
    current_user: User = Depends(require_roles(UserRole.CITIZEN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Update a parcel's details. Only allowed if the parcel is in BOOKED status (or if admin).
    Recalculates server-side tariff if specifications change.
    """
    parcel = get_parcel_by_tracking_id(db=db, tracking_id=tracking_id, current_user=current_user)
    
    if parcel.status != "BOOKED" and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EDIT_NOT_ALLOWED", "message": "Can only edit parcels in BOOKED status."}
        )
        
    is_admin = current_user.role == UserRole.ADMIN
    updated_parcel = update_parcel(
        db=db,
        parcel=parcel,
        parcel_update=parcel_in,
        is_admin_override=is_admin and parcel_in.price is not None
    )
    return ApiResponse.ok(data=ParcelResponse.model_validate(updated_parcel))
