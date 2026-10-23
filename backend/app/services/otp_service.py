import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.parcel import Parcel
from app.models.enums import ParcelTrackingStatus
from app.models.tracking import DeliveryOTP
from app.auth.security import hash_password, verify_password
from app.config import settings

logger = logging.getLogger(__name__)


def generate_delivery_otp(db: Session, parcel: Parcel) -> Tuple[DeliveryOTP, str]:
    """
    Generates a cryptographically random 6-digit numeric OTP for delivery confirmation.
    Stored strictly as an Argon2id hash. Plaintext is never persisted.
    Configured for validity window and max 5 attempts.
    """
    if parcel.status != ParcelTrackingStatus.OUT_FOR_DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "DELIVERY_NOT_ALLOWED",
                "message": f"Delivery verification code can only be generated when parcel is OUT_FOR_DELIVERY (Current: {parcel.status})."
            }
        )

    now = datetime.now(timezone.utc)

    # Invalidate any prior unverified OTP records for this parcel
    prior_unverified = (
        db.query(DeliveryOTP)
        .filter(DeliveryOTP.parcel_id == parcel.id, DeliveryOTP.verified_at.is_(None))
        .all()
    )
    for old_otp in prior_unverified:
        old_otp.expires_at = now
        old_otp.attempts = old_otp.max_attempts
    if prior_unverified:
        db.flush()

    # Cryptographically random 6-digit number (100000 - 999999)
    raw_otp = str(secrets.randbelow(900000) + 100000)

    # Securely hash OTP using Argon2id
    otp_hash = hash_password(raw_otp)
    expires_at = now + timedelta(minutes=settings.OTP_VALIDITY_MINUTES)

    otp_record = DeliveryOTP(
        parcel_id=parcel.id,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempts=0,
        max_attempts=5,
        created_at=now
    )

    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)

    logger.info(f"Generated new Delivery OTP for Parcel {parcel.tracking_id} (Expires: {expires_at.isoformat()})")
    return otp_record, raw_otp


def verify_delivery_otp(db: Session, parcel: Parcel, entered_otp: str) -> DeliveryOTP:
    """
    Verifies the submitted 6-digit OTP against the stored Argon2id hash.
    Protects against replay, attempt exhaustion, and race conditions using row-level locking.
    Always retrieves the latest issued OTP for the parcel ordered by ID descending.
    """
    now = datetime.now(timezone.utc)

    # Query active unverified OTP by ID descending (most recent first)
    query = (
        db.query(DeliveryOTP)
        .filter(DeliveryOTP.parcel_id == parcel.id)
        .order_by(DeliveryOTP.id.desc())
    )

    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        query = query.with_for_update()

    otp_record = query.first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "OTP_NOT_FOUND", "message": "No delivery OTP has been issued for this parcel."}
        )

    # Check if already verified
    if otp_record.verified_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_ALREADY_USED", "message": "This delivery verification code has already been used."}
        )

    # Check expiration
    # Ensure timezone-aware comparison
    record_expiry = otp_record.expires_at
    if record_expiry.tzinfo is None:
        record_expiry = record_expiry.replace(tzinfo=timezone.utc)

    if record_expiry < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_EXPIRED", "message": "Delivery verification code has expired. Please request a new code."}
        )

    # Check attempt limit
    if otp_record.attempts >= otp_record.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_ATTEMPT_LIMIT_EXCEEDED", "message": "Maximum verification attempts exceeded. Please request a new OTP."}
        )

    # Verify entered OTP
    is_valid = verify_password(entered_otp.strip(), otp_record.otp_hash)

    if not is_valid:
        otp_record.attempts += 1
        db.add(otp_record)
        db.commit()
        remaining = otp_record.max_attempts - otp_record.attempts
        logger.warning(f"Failed OTP attempt for Parcel {parcel.tracking_id}. Attempts remaining: {remaining}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "OTP_INVALID",
                "message": f"The delivery verification code is invalid. Remaining attempts: {remaining}."
            }
        )

    # Mark verified
    otp_record.verified_at = now
    db.add(otp_record)
    # Don't commit yet; caller will commit along with DELIVERED status transition atomically
    return otp_record
