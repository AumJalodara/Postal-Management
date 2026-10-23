from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from app.config import settings
from app.services.route_optimization import RouteResult

@dataclass
class ETAResult:
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


def calculate_eta(
    route: RouteResult, 
    start_time: Optional[datetime] = None,
    speed_kmph: Optional[float] = None,
    service_time_per_stop: Optional[float] = None,
    buffer_minutes: Optional[float] = None
) -> ETAResult:
    """
    Calculates a heuristic Estimated Time of Arrival (ETA) for a given geographic route.
    
    The estimate relies purely on geographic Haversine distance from the RouteResult, 
    an average operational speed, service time per routable stop, and an operational buffer.
    It does not utilize live GPS, traffic APIs, or road network logic.
    """
    
    # 1. Configuration Validation and Resolution
    speed = speed_kmph if speed_kmph is not None else settings.ETA_AVERAGE_SPEED_KMPH
    service_time = service_time_per_stop if service_time_per_stop is not None else settings.ETA_SERVICE_TIME_MINUTES_PER_STOP
    buf_time = buffer_minutes if buffer_minutes is not None else settings.ETA_BUFFER_MINUTES
    
    if speed <= 0:
        raise ValueError(f"Average speed must be greater than 0, got {speed}")
    if service_time < 0:
        raise ValueError(f"Service time must be non-negative, got {service_time}")
    if buf_time < 0:
        raise ValueError(f"Buffer must be non-negative, got {buf_time}")

    # 2. Extract Data from Route
    dist_km = route.optimized_distance_km
    if dist_km < 0:
        dist_km = 0.0
        
    routable_stops = len(route.stops)
    unresolved_stops = len(route.unresolved_stops)
    unresolved_ids = [s.stop_id for s in route.unresolved_stops]

    # 3. Calculate Travel Time
    # (distance / speed) gives hours. multiply by 60 for minutes.
    travel_time_mins = (dist_km / speed) * 60.0

    # 4. Calculate Service Time
    # We only spend service time at routable stops (valid coordinates).
    service_time_mins = routable_stops * service_time

    # 5. Determine Buffer
    # We apply the buffer to the entire route. If there are NO routable stops AND no distance, 
    # it might make sense to apply 0 buffer, but we follow a deterministic rule:
    # If route is completely empty (no distance and no valid stops), total ETA is 0.
    if routable_stops == 0 and dist_km == 0.0:
        travel_time_mins = 0.0
        service_time_mins = 0.0
        actual_buffer = 0.0
    else:
        actual_buffer = buf_time

    # 6. Total ETA
    total_eta_mins = travel_time_mins + service_time_mins + actual_buffer
    
    # 7. Estimated Completion Time
    est_completion = None
    if start_time is not None:
        # We explicitly preserve the start_time's timezone awareness (or lack thereof) by directly adding timedelta
        est_completion = start_time + timedelta(minutes=total_eta_mins)

    # Compile assumptions for explainability
    assumptions = {
        "distance_model": "Haversine geographic distance",
        "route_source": "Module 4 Step 5 Optimized Route",
        "average_speed_kmph": speed,
        "service_time_per_stop_mins": service_time,
        "buffer_mins": buf_time,
        "traffic_included": False,
        "live_gps_included": False,
        "road_network_routing": False,
        "timezone_aware": start_time.tzinfo is not None if start_time else None
    }

    return ETAResult(
        agent_id=route.agent_id,
        route_distance_km=dist_km,
        routable_stop_count=routable_stops,
        unresolved_stop_count=unresolved_stops,
        unresolved_stop_ids=unresolved_ids,
        average_speed_kmph=speed,
        travel_time_minutes=travel_time_mins,
        service_time_minutes=service_time_mins,
        buffer_minutes=actual_buffer,
        total_eta_minutes=total_eta_mins,
        estimated_completion_time=est_completion,
        assumptions=assumptions
    )
