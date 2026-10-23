from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class OperationalHistory(Base):
    __tablename__ = "operational_history"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), index=True, nullable=False)
    entity_type = Column(String(100), index=True, nullable=False)
    entity_id = Column(Integer, index=True, nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    previous_status = Column(String(100), nullable=True)
    new_status = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
