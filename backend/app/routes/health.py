from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.connection import get_db
from app.schemas.common import ApiResponse

router = APIRouter(tags=["System Health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Liveness probe and database connectivity verification."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return ApiResponse.ok(data={
        "status": "UP",
        "database": db_status,
        "module": "Module 1 — User, Parcel Booking & Doorstep Pickup Management",
        "system": "AI-Powered Intelligent Government Postal Management Prototype"
    })
