from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime

class OperationsAgentSummary(BaseModel):
    agent_id: int
    name: str
    phone: str
    service_area: str
    is_available: bool
    active_pickup_count: int
    last_assigned_at: Optional[datetime]

class OperationsRouteStop(BaseModel):
    stop_id: str
    pickup_id: int
    pin: str
    latitude: Optional[float]
    longitude: Optional[float]
    stop_type: str
    sequence: int

class OperationsRouteResponse(BaseModel):
    agent_id: int
    start_location: Dict[str, Any]
    stops: List[OperationsRouteStop]
    total_distance_km: float
    initial_distance_km: float
    optimized_distance_km: float
    improvement_percent: float
    algorithm: str
    unresolved_stops: List[OperationsRouteStop]

class OperationsETAResponse(BaseModel):
    agent_id: int
    route_distance_km: float
    routable_stop_count: int
    unresolved_stop_count: int
    unresolved_stop_ids: List[str]
    average_speed_kmph: float
    travel_time_minutes: float
    service_time_minutes: float
    buffer_minutes: float
    total_eta_minutes: float
    estimated_completion_time: Optional[datetime]
    assumptions: Dict[str, Any]

class OperationsAgentDetail(BaseModel):
    agent: OperationsAgentSummary
    route: OperationsRouteResponse
    eta: OperationsETAResponse

class OperationsPickupSummary(BaseModel):
    id: int
    parcel_id: int
    requester_id: int
    assigned_agent_id: Optional[int]
    status: str
    pickup_pin: str
    requested_date: str

class OperationsHistoryResponse(BaseModel):
    id: int
    event_type: str
    entity_type: str
    entity_id: int
    actor_user_id: Optional[int]
    agent_id: Optional[int]
    previous_status: Optional[str]
    new_status: Optional[str]
    description: Optional[str]
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

class OperationsHistoryListResponse(BaseModel):
    items: List[OperationsHistoryResponse]
    page: int
    page_size: int
    total_count: int

class OperationsAssistantRequest(BaseModel):
    query: str

class OperationsAssistantResponse(BaseModel):
    answer: str


class OperationsCitizenSummary(BaseModel):
    citizen_id: int
    name: str
    email: str
    phone: str
    is_active: bool
    registered_at: Optional[datetime]
    parcels_booked_count: int
    active_parcels_count: int
    delivered_parcels_count: int
    pickups_requested_count: int
    total_spent: float
    last_booking_date: Optional[datetime]


class OperationsCitizenMetrics(BaseModel):
    total_registered_citizens: int
    citizens_with_bookings: int
    total_parcels_booked: int
    total_pickups_requested: int
    total_revenue: float
    average_parcels_per_citizen: float


class OperationsCitizensResponse(BaseModel):
    metrics: OperationsCitizenMetrics
    citizens: List[OperationsCitizenSummary]


class OperationsCitizenParcelItem(BaseModel):
    id: int
    tracking_id: str
    receiver_name: str
    receiver_phone: str
    destination_city: str
    destination_state: str
    destination_pin: str
    parcel_type: str
    priority: str
    weight: float
    price: float
    status: str
    created_at: datetime



