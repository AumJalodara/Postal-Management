import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.config import settings
from app.auth.limiter import limiter
from app.models.user import User
from app.models.revoked_token import RevokedToken
from app.models.enums import UserRole
from app.schemas.user import UserRegister, UserLogin, UserUpdate, UserResponse, TokenResponse
from app.schemas.common import ApiResponse
from app.auth.security import hash_password, verify_password, create_access_token, decode_access_token, get_token_hash
from app.auth.dependencies import get_current_user, security_scheme

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def register_user(request: Request, user_in: UserRegister, db: Session = Depends(get_db)):
    """
    Public Citizen Registration endpoint.
    Strict Security Rule: Always creates users with role CITIZEN.
    Anonymous users cannot register as AGENT or ADMIN.
    """
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_EXISTS", "message": "An account with this email address already exists."}
        )

    # Hash password with Argon2id
    hashed_pwd = hash_password(user_in.password)

    user = User(
        name=user_in.name,
        email=user_in.email,
        phone=user_in.phone,
        password_hash=hashed_pwd,
        role=UserRole.CITIZEN,  # Forced server-side role
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"New citizen registered: #{user.id} ({user.email})")
    return ApiResponse.ok(data=UserResponse.model_validate(user))


@router.post("/login", response_model=ApiResponse[TokenResponse])
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, user_in: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and issue JWT bearer token."""
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        logger.warning(f"Failed login attempt for {user_in.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "INACTIVE_ACCOUNT", "message": "This account is inactive. Please contact support."}
        )

    token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role.value,
        "email": user.email
    })

    logger.info(f"User #{user.id} logged in successfully (Role: {user.role.value})")
    return ApiResponse.ok(data=TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=user.role
    ))


@router.get("/me", response_model=ApiResponse[UserResponse])
def get_me(current_user: User = Depends(get_current_user)):
    """Return profile for currently authenticated user."""
    return ApiResponse.ok(data=UserResponse.model_validate(current_user))


@router.put("/me", response_model=ApiResponse[UserResponse])
def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update permitted profile fields (name, phone) for the currently authenticated user.
    Protected fields such as role, email, and is_active cannot be modified here.
    """
    updated = False
    if user_update.name is not None and user_update.name.strip():
        current_user.name = user_update.name.strip()
        updated = True

    if user_update.phone is not None and user_update.phone.strip():
        current_user.phone = user_update.phone.strip()
        updated = True

    if updated:
        db.commit()
        db.refresh(current_user)
        logger.info(f"User #{current_user.id} updated their profile.")

    return ApiResponse.ok(data=UserResponse.model_validate(current_user))


@router.post("/logout", response_model=ApiResponse[dict])
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Securely revokes the current JWT bearer token, preventing subsequent access even
    if the token is copied or retained client-side.
    """
    if credentials and credentials.credentials:
        token = credentials.credentials
        try:
            payload = decode_access_token(token)
            exp_ts = payload.get("exp")
            if exp_ts:
                expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            else:
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
        except Exception:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)

        token_hash = get_token_hash(token)
        existing = db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first()
        if not existing:
            revocation_entry = RevokedToken(
                token_hash=token_hash,
                expires_at=expires_at
            )
            db.add(revocation_entry)
            
            # Prune old expired tokens from the revocation table
            db.query(RevokedToken).filter(RevokedToken.expires_at < datetime.now(timezone.utc)).delete()
            db.commit()
            logger.info(f"User #{current_user.id} logged out. Token revoked.")

    return ApiResponse.ok(data={"message": "Logged out successfully. Token revoked."})
