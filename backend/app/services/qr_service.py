import io
import base64
import secrets
import logging
from typing import Tuple, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
import qrcode

from app.models.parcel import Parcel
from app.models.tracking import ParcelQRCode, ParcelTrackingEvent
from app.schemas.tracking import PublicTrackingResponse, TrackingEventResponse

logger = logging.getLogger(__name__)


def mask_text(text: str) -> str:
    """
    Privacy masking for sensitive citizen details in public tracking.
    Example: 'Rahul Kumar' -> 'R**** K****'
    """
    if not text:
        return "****"
    words = text.strip().split()
    masked_words = []
    for w in words:
        if len(w) <= 1:
            masked_words.append(w)
        else:
            masked_words.append(w[0] + "*" * (len(w) - 1))
    return " ".join(masked_words)


def generate_qr_base64_image(payload: str) -> str:
    """Generates PNG QR code and returns as base64 data URI."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


def get_or_create_parcel_qr(
    db: Session,
    parcel: Parcel,
    base_url: Optional[str] = None
) -> Tuple[ParcelQRCode, str, str]:
    """
    Idempotently returns or generates a secure, opaque QR code for a parcel.
    Does NOT encode sensitive user data inside the QR.
    Returns (qr_record, qr_base64_image, payload_url).
    """
    if not base_url:
        from app.config import settings
        base_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")

    # Check for existing active QR code
    existing_qr = (
        db.query(ParcelQRCode)
        .filter(ParcelQRCode.parcel_id == parcel.id, ParcelQRCode.revoked_at.is_(None))
        .first()
    )

    if existing_qr:
        payload_url = f"{base_url}/track/qr/{existing_qr.qr_token}"
        img_b64 = generate_qr_base64_image(payload_url)
        return existing_qr, img_b64, payload_url

    # Generate cryptographically secure unguessable opaque token
    token = f"GPMQR-{secrets.token_urlsafe(24)}"
    new_qr = ParcelQRCode(
        parcel_id=parcel.id,
        qr_token=token,
    )
    db.add(new_qr)
    db.commit()
    db.refresh(new_qr)

    payload_url = f"{base_url}/track/qr/{token}"
    img_b64 = generate_qr_base64_image(payload_url)
    logger.info(f"Generated new QR code for Parcel {parcel.tracking_id} (Token: {token})")
    return new_qr, img_b64, payload_url


def resolve_qr_code(db: Session, qr_token: str) -> PublicTrackingResponse:
    """
    Resolves an opaque QR token and returns a privacy-masked public tracking timeline.
    Guarantees no raw personal information, passwords, OTPs, or DB IDs are leaked.
    """
    if not qr_token or not qr_token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "QR_INVALID", "message": "Invalid QR code format."}
        )

    qr_record = (
        db.query(ParcelQRCode)
        .options(
            joinedload(ParcelQRCode.parcel).joinedload(Parcel.tracking_events),
            joinedload(ParcelQRCode.parcel).joinedload(Parcel.sender)
        )
        .filter(ParcelQRCode.qr_token == qr_token.strip())
        .first()
    )

    if not qr_record:
        # Also support resolving directly if a parcel tracking ID (e.g. GPM-2026-...) was scanned/entered
        parcel_by_id = (
            db.query(Parcel)
            .options(
                joinedload(Parcel.tracking_events),
                joinedload(Parcel.sender)
            )
            .filter(Parcel.tracking_id == qr_token.strip())
            .first()
        )
        if parcel_by_id:
            qr_record, _, _ = get_or_create_parcel_qr(db, parcel_by_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "QR_NOT_FOUND", "message": "The scanned QR code is not recognized by the postal system."}
            )

    if qr_record.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "QR_REVOKED", "message": "This QR tracking code has been revoked or invalidated."}
        )

    parcel = qr_record.parcel
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PARCEL_NOT_FOUND", "message": "Associated consignment record not found."}
        )

    # Privacy-masked sender and receiver representations
    sender_name = parcel.sender.name if parcel.sender else "Citizen Sender"
    sender_masked = mask_text(sender_name)
    receiver_masked = mask_text(parcel.receiver_name)

    # Chronological timeline events
    events = (
        db.query(ParcelTrackingEvent)
        .filter(ParcelTrackingEvent.parcel_id == parcel.id)
        .order_by(ParcelTrackingEvent.created_at.asc())
        .all()
    )

    last_updated = events[-1].created_at if events else parcel.updated_at

    return PublicTrackingResponse(
        tracking_id=parcel.tracking_id,
        current_status=parcel.status,
        sender_masked=sender_masked,
        receiver_masked=receiver_masked,
        destination_city=parcel.destination_city,
        destination_pin=parcel.destination_pin,
        last_updated=last_updated,
        timeline=[TrackingEventResponse.model_validate(e) for e in events]
    )
