import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.config import settings
from app.auth.limiter import limiter
from app.models.user import User
from app.models.parcel import Parcel
from app.models.delivery_agent import DeliveryAgent
from app.models.pickup import PickupRequest
from app.models.enums import UserRole, ParcelTrackingStatus
from app.schemas.common import ApiResponse
from app.schemas.tracking import (
    TrackingEventResponse,
    TrackingTimelineResponse,
    PublicTrackingResponse,
    QRCodeResponse,
    QRResolveRequest,
    TrackingEventCreateRequest,
    DeliveryOTPResponse,
    DeliveryVerifyRequest,
    DeliveryVerifyResponse,
)
from app.auth.dependencies import get_current_user, require_roles
from app.services.qr_service import get_or_create_parcel_qr, resolve_qr_code
from app.services.otp_service import generate_delivery_otp
from app.services.delivery_service import process_secure_delivery
from app.services.tracking_state_machine import transition_parcel_tracking

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tracking & Secure Delivery"])


def get_parcel_or_404(db: Session, tracking_id: str) -> Parcel:
    parcel = db.query(Parcel).filter(Parcel.tracking_id == tracking_id.strip()).first()
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PARCEL_NOT_FOUND", "message": f"Consignment {tracking_id} not found."}
        )
    return parcel


def verify_parcel_access(parcel: Parcel, user: User, db: Session):
    """Verify user is sender, admin, or agent handling this parcel."""
    if user.role == UserRole.ADMIN:
        return
    if user.id == parcel.sender_id:
        return
    if user.role == UserRole.AGENT:
        agent = db.query(DeliveryAgent).filter(DeliveryAgent.user_id == user.id).first()
        if agent:
            # Check 1: Agent assigned to pickup
            pickup = db.query(PickupRequest).filter(
                PickupRequest.parcel_id == parcel.id,
                PickupRequest.assigned_agent_id == agent.id
            ).first()
            if pickup:
                return
            # Check 2: Agent service area matches parcel destination PIN or postal circle
            from app.services.delivery_service import is_agent_authorized_for_pin
            if is_agent_authorized_for_pin(agent.service_area, parcel.destination_pin):
                return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "ACCESS_DENIED", "message": "You are not authorized to access this parcel."}
    )



# --------------------------------------------------------------------------
# QR CODE GENERATION & RESOLUTION
# --------------------------------------------------------------------------

@router.get("/parcels/{tracking_id}/qr", response_model=ApiResponse[QRCodeResponse])
def get_parcel_qr(
    tracking_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve or generate the opaque QR tracking code for a parcel.
    Authorized for sender, assigned agent, and admin.
    """
    parcel = get_parcel_or_404(db, tracking_id)
    verify_parcel_access(parcel, current_user, db)

    qr_record, img_b64, payload_url = get_or_create_parcel_qr(db, parcel)
    return ApiResponse.ok(
        data=QRCodeResponse(
            tracking_id=parcel.tracking_id,
            qr_token=qr_record.qr_token,
            qr_code_base64=img_b64,
            payload_url=payload_url,
            created_at=qr_record.created_at
        )
    )


@router.post("/parcels/{tracking_id}/qr", response_model=ApiResponse[QRCodeResponse])
def create_parcel_qr(
    tracking_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Idempotently generate or retrieve QR code for a parcel.
    """
    parcel = get_parcel_or_404(db, tracking_id)
    verify_parcel_access(parcel, current_user, db)

    qr_record, img_b64, payload_url = get_or_create_parcel_qr(db, parcel)
    return ApiResponse.ok(
        data=QRCodeResponse(
            tracking_id=parcel.tracking_id,
            qr_token=qr_record.qr_token,
            qr_code_base64=img_b64,
            payload_url=payload_url,
            created_at=qr_record.created_at
        )
    )


@router.post("/qr/resolve", response_model=ApiResponse[PublicTrackingResponse])
def scan_and_resolve_qr(
    body: QRResolveRequest,
    db: Session = Depends(get_db)
):
    """
    Public endpoint: Scans/resolves an opaque QR token.
    Returns masked tracking timeline without exposing sensitive personal data.
    """
    tracking_info = resolve_qr_code(db, body.qr_token)
    return ApiResponse.ok(data=tracking_info)


# --------------------------------------------------------------------------
# PARCEL TRACKING TIMELINE
# --------------------------------------------------------------------------

@router.get("/parcels/{tracking_id}/tracking", response_model=ApiResponse[PublicTrackingResponse])
def get_parcel_tracking_timeline(
    tracking_id: str,
    db: Session = Depends(get_db)
):
    """
    Public tracking timeline view by tracking ID.
    Returns privacy-masked sender and receiver details with chronological events.
    """
    parcel = get_parcel_or_404(db, tracking_id)

    qr_record, _, _ = get_or_create_parcel_qr(db, parcel)
    tracking_info = resolve_qr_code(db, qr_record.qr_token)
    return ApiResponse.ok(data=tracking_info)


@router.get("/parcels/{tracking_id}/events", response_model=ApiResponse[List[TrackingEventResponse]])
def get_parcel_tracking_events(
    tracking_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve list of chronological tracking events for a parcel.
    """
    parcel = get_parcel_or_404(db, tracking_id)
    events = [TrackingEventResponse.model_validate(e) for e in parcel.tracking_events]
    return ApiResponse.ok(data=events)


# --------------------------------------------------------------------------
# AGENT EVENT UPDATES & STATE TRANSITIONS
# --------------------------------------------------------------------------

@router.post("/parcels/{tracking_id}/events", response_model=ApiResponse[TrackingEventResponse])
def add_parcel_tracking_event(
    tracking_id: str,
    event_in: TrackingEventCreateRequest,
    current_user: User = Depends(require_roles(UserRole.AGENT, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Update parcel tracking state (IN_TRANSIT, ARRIVED_AT_HUB, OUT_FOR_DELIVERY, DELIVERY_ATTEMPTED).
    Transitioning directly to DELIVERED via this endpoint is strictly prohibited (must use verify-delivery).
    """
    parcel = get_parcel_or_404(db, tracking_id)

    if event_in.new_status == ParcelTrackingStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "DELIVERY_NOT_ALLOWED",
                "message": "Cannot mark parcel as DELIVERED without OTP verification. Use /verify-delivery."
            }
        )

    event = transition_parcel_tracking(
        db=db,
        parcel=parcel,
        target_status=event_in.new_status,
        location_label=event_in.location_label,
        description=event_in.description,
        actor_user=current_user
    )

    return ApiResponse.ok(data=TrackingEventResponse.model_validate(event))


# --------------------------------------------------------------------------
# DELIVERY OTP GENERATION & SECURE VERIFICATION
# --------------------------------------------------------------------------

@router.post("/parcels/{tracking_id}/delivery-otp", response_model=ApiResponse[DeliveryOTPResponse])
@limiter.limit(settings.RATE_LIMIT_OTP)
def request_delivery_otp(
    request: Request,
    tracking_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate 6-digit delivery verification OTP.
    Only permitted when parcel status is OUT_FOR_DELIVERY.
    In prototype environment, returns test_otp for demonstration and testing.
    """
    parcel = get_parcel_or_404(db, tracking_id)
    verify_parcel_access(parcel, current_user, db)

    otp_record, raw_otp = generate_delivery_otp(db, parcel)

    is_prod = getattr(settings, "APPLICATION_ENV", "development") == "production"
    test_otp_val = None if is_prod else raw_otp

    exp = otp_record.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    response_data = DeliveryOTPResponse(
        tracking_id=parcel.tracking_id,
        expires_at=exp,
        message=f"Delivery verification code generated. Valid for {settings.OTP_VALIDITY_MINUTES} minutes.",
        test_otp=test_otp_val
    )
    return ApiResponse.ok(data=response_data)


@router.post("/parcels/{tracking_id}/verify-delivery", response_model=ApiResponse[DeliveryVerifyResponse])
def verify_parcel_delivery(
    tracking_id: str,
    verify_in: DeliveryVerifyRequest,
    current_user: User = Depends(require_roles(UserRole.AGENT, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Secure Delivery Confirmation:
    Submits recipient OTP, verifies Argon2id hash, transitions status to DELIVERED,
    and logs immutable delivery event.
    """
    parcel = get_parcel_or_404(db, tracking_id)
    result = process_secure_delivery(db, parcel, verify_in.otp, current_user)
    return ApiResponse.ok(data=result)
