from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database.connection import get_next_tracking_sequence


def generate_prototype_tracking_id(db: Session) -> str:
    """
    Generates a unique, concurrency-safe prototype tracking identifier.
    Format: GPM-{YEAR}-{SEQUENCE:06d}
    Example: GPM-2026-000001
    
    Academic Prototype Notice: This is NOT an official India Post article number.
    """
    current_year = datetime.now(timezone.utc).year
    seq_val = get_next_tracking_sequence(db)
    return f"GPM-{current_year}-{seq_val:06d}"
