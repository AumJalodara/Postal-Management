from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DeliveryAgentResponse(BaseModel):
    id: int
    user_id: int
    service_area: str
    is_available: bool
    active_pickup_count: int
    last_assigned_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PickupTransitionRequest(BaseModel):
    reason: Optional[str] = None
