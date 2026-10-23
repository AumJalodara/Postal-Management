import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from app.config import settings
from app.auth.limiter import limiter, custom_rate_limit_exceeded_handler
from app.routes import auth, parcels, pickups, agent, health, tracking, postal, operations

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smart_postal")


def ensure_default_seed_data():
    """Ensure database tables and baseline demo users (Admin, Agents, Citizen) are initialized."""
    from app.database.connection import engine, SessionLocal
    from app.database.base import Base
    from app.models.user import User
    from app.models.delivery_agent import DeliveryAgent
    from app.models.enums import UserRole
    from app.auth.security import hash_password

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Admin
        admin_email = "admin@postal.gov.in"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                name="System Administrator",
                email=admin_email,
                phone="9876500001",
                password_hash=hash_password("Admin@12345"),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            logger.info("Initialized default Admin account (admin@postal.gov.in)")

        # 2. Delivery Agents (All 36 States & Union Territories)
        from app.database.seed_agents import STATE_AGENTS_DATA
        for ag in STATE_AGENTS_DATA:
            u = db.query(User).filter(User.email == ag["email"]).first()
            if not u:
                u = User(
                    name=ag["name"],
                    email=ag["email"],
                    phone=ag["phone"],
                    password_hash=hash_password("Agent@12345"),
                    role=UserRole.AGENT,
                    is_active=True
                )
                db.add(u)
                db.flush()

            agent_profile = db.query(DeliveryAgent).filter(DeliveryAgent.user_id == u.id).first()
            if not agent_profile:
                agent_profile = DeliveryAgent(
                    user_id=u.id,
                    service_area=ag["pin"],
                    is_available=True,
                    active_pickup_count=0
                )
                db.add(agent_profile)
                logger.info(f"Initialized Delivery Agent: {ag['email']} ({ag['state']})")

        # 3. Demo Citizen
        citizen_email = "citizen.demo@example.com"
        citizen = db.query(User).filter(User.email == citizen_email).first()
        if not citizen:
            citizen = User(
                name="Rahul Sharma",
                email=citizen_email,
                phone="9876543210",
                password_hash=hash_password("Citizen@12345"),
                role=UserRole.CITIZEN,
                is_active=True
            )
            db.add(citizen)
            logger.info("Initialized Demo Citizen account (citizen.demo@example.com)")

        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Seed initialization check failed: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_default_seed_data()
    except Exception as exc:
        logger.warning(f"Non-fatal error during startup seeding: {exc}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Academic prototype for AI-Powered Intelligent Government Postal Management System (Modules 1 & 2). Not official India Post software.",
    version="1.1.0",
    lifespan=lifespan
)

# Register slowapi rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

# CORS Configuration for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Exception Handlers to enforce uniform API Error Envelope
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "HTTP_ERROR")
        message = detail.get("message", str(detail))
    else:
        code = f"HTTP_{exc.status_code}"
        message = str(detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "Invalid request parameters.")
    loc = " -> ".join([str(l) for l in first_error.get("loc", [])])
    
    # Safe JSON-serializable representation of validation errors
    clean_details = [
        {
            "loc": [str(x) for x in err.get("loc", [])],
            "msg": err.get("msg"),
            "type": err.get("type")
        }
        for err in errors
    ]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": f"{loc}: {msg}",
                "details": clean_details
            }
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please contact technical support."
            }
        }
    )


# Register Routers
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(parcels.router, prefix=settings.API_V1_PREFIX)
app.include_router(pickups.router, prefix=settings.API_V1_PREFIX)
app.include_router(agent.router, prefix=settings.API_V1_PREFIX)
app.include_router(tracking.router, prefix=settings.API_V1_PREFIX)
app.include_router(postal.router, prefix=settings.API_V1_PREFIX)
app.include_router(operations.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "prototype": "AI-Powered Intelligent Government Postal Management System",
        "module": "Modules 1 & 2: User, Parcel Booking, Doorstep Pickup & QR-Based Parcel Tracking & Secure Delivery",
        "docs": "/docs",
        "api_prefix": settings.API_V1_PREFIX
    }
