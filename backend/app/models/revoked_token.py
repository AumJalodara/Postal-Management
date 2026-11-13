from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.database.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    revoked_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

