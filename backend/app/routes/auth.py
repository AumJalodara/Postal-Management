import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.config import settings
from app.auth.limiter import limiter
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.schemas.common import ApiResponse
from app.auth.security import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user

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
