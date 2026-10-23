import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.models.pickup import PickupRequest
from app.models.enums import PickupStatus
from app.services.postal_location_service import postal_location_service
from app.services.geospatial_engine import haversine_distance, InvalidCoordinateError

logger = logging.getLogger(__name__)

@dataclass
class RouteStop:
    stop_id: str
    pickup_id: int
    pin: str
    latitude: Optional[float]
    longitude: Optional[float]
    stop_type: str
    sequence: int = -1

@dataclass
class RouteResult:
    agent_id: int
    start_location: Dict[str, Any]
    stops: List[RouteStop]
    total_distance_km: float
    initial_distance_km: float
    optimized_distance_km: float
    improvement_percent: float
    algorithm: str
    unresolved_stops: List[RouteStop]


def build_optimized_route(agent_id: int, agent_service_pin: str, assigned_pickups: List[PickupRequest]) -> RouteResult:
    """
    Constructs a geographic heuristic optimized route for an agent's assigned pickups.
    Algorithm: Haversine geographic distance + Greedy Nearest Neighbor + 2-opt local improvement.
    
    The agent's service area PIN serves as the starting reference coordinate (not live GPS).
    Only pickups in ASSIGNED or ACCEPTED status are routed.
    Pickups lacking valid coordinates are excluded from optimization and returned in `unresolved_stops`.
    """
    algorithm_name = "Haversine + Greedy Nearest Neighbor + 2-opt"

    # 1. Resolve starting location
    start_loc = postal_location_service.get_location_for_pin(agent_service_pin)
    start_lat = start_loc.get("latitude") if start_loc else None
    start_lon = start_loc.get("longitude") if start_loc else None

    # If the agent has no valid starting coordinate, we cannot meaningfully route.
    # We will treat the starting distance as 0 to the first stop, but this is a fallback.
    start_point = None
    if start_lat is not None and start_lon is not None:
        start_point = (start_lat, start_lon)

    # 2. Filter and resolve stops
    valid_stops = []
    unresolved_stops = []

    # Only include pickups that haven't been picked up or cancelled
    routeable_statuses = {PickupStatus.ASSIGNED, PickupStatus.ACCEPTED}
    routeable_pickups = [p for p in assigned_pickups if p.status in routeable_statuses]

    for p in routeable_pickups:
        loc = postal_location_service.get_location_for_pin(p.pickup_pin)
        lat = loc.get("latitude") if loc else None
        lon = loc.get("longitude") if loc else None
        
        stop = RouteStop(
            stop_id=f"pickup_{p.id}",
            pickup_id=p.id,
            pin=p.pickup_pin,
            latitude=lat,
            longitude=lon,
            stop_type="PICKUP"
        )
        
        if lat is not None and lon is not None:
            valid_stops.append(stop)
        else:
            unresolved_stops.append(stop)

    # Handle empty valid stops
    if not valid_stops:
        return RouteResult(
            agent_id=agent_id,
            start_location={"pin": agent_service_pin, "latitude": start_lat, "longitude": start_lon},
            stops=[],
            total_distance_km=0.0,
            initial_distance_km=0.0,
            optimized_distance_km=0.0,
            improvement_percent=0.0,
            algorithm=algorithm_name,
            unresolved_stops=unresolved_stops
        )

    # Pre-cache pairwise distances to avoid recalculating
    # We treat start_point as index -1
    def get_distance(p1, p2):
        if p1 is None or p2 is None:
            return 0.0
        try:
            return haversine_distance(p1[0], p1[1], p2[0], p2[1])
        except InvalidCoordinateError:
            return 0.0

    # 3. Greedy Nearest Neighbor
    unvisited = list(valid_stops)
    # Sort deterministically first to ensure tie-breaking starts from a stable state
    unvisited.sort(key=lambda s: s.pickup_id)
    
    route = []
    current_point = start_point

    while unvisited:
        best_stop = None
        best_dist = float('inf')
        
        for stop in unvisited:
            stop_point = (stop.latitude, stop.longitude)
            dist = get_distance(current_point, stop_point)
            
            # Tie-breaking: if distance is equal, it falls back to the deterministic order we sorted initially
            if dist < best_dist:
                best_dist = dist
                best_stop = stop
                
        route.append(best_stop)
        unvisited.remove(best_stop)
        current_point = (best_stop.latitude, best_stop.longitude)

    initial_route = list(route)
    initial_distance_km = _calculate_route_distance(start_point, initial_route, get_distance)

    # 4. 2-opt Local Improvement
    # The route is just the list of stops (excluding start point which is fixed).
    optimized_route, optimized_distance_km = _two_opt(start_point, initial_route, initial_distance_km, get_distance)

    # Calculate improvement
    improvement_percent = 0.0
    if initial_distance_km > 0:
        improvement_percent = ((initial_distance_km - optimized_distance_km) / initial_distance_km) * 100.0

    # 5. Finalize sequence
    for i, stop in enumerate(optimized_route):
        stop.sequence = i + 1

    for stop in unresolved_stops:
        stop.sequence = -1

    return RouteResult(
        agent_id=agent_id,
        start_location={"pin": agent_service_pin, "latitude": start_lat, "longitude": start_lon},
        stops=optimized_route,
        total_distance_km=optimized_distance_km,
        initial_distance_km=initial_distance_km,
        optimized_distance_km=optimized_distance_km,
        improvement_percent=improvement_percent,
        algorithm=algorithm_name,
        unresolved_stops=unresolved_stops
    )


def _calculate_route_distance(start_point, route_stops: List[RouteStop], dist_func) -> float:
    if not route_stops:
        return 0.0
    total = 0.0
    curr = start_point
    for stop in route_stops:
        stop_point = (stop.latitude, stop.longitude)
        total += dist_func(curr, stop_point)
        curr = stop_point
    return total


def _two_opt(start_point, route: List[RouteStop], current_best_dist: float, dist_func) -> tuple[List[RouteStop], float]:
    """
    Applies the 2-opt algorithm to improve the route.
    Start point is fixed.
    """
    n = len(route)
    if n <= 1:
        return route, current_best_dist

    improved = True
    best_route = list(route)
    
    # Pre-calculate points array for quick access
    # index 0 is start point (if not None), 1..n are route stops
    points = [start_point] + [(s.latitude, s.longitude) for s in best_route]
    
    while improved:
        improved = False
        for i in range(1, n):
            for j in range(i + 1, n + 1):
                # Compare the edges to be broken vs new edges
                # Current edges: points[i-1] -> points[i] and points[j-1] -> points[j]
                # New edges: points[i-1] -> points[j-1] and points[i] -> points[j]
                
                # Careful: if j == n, points[j] doesn't exist (no return to depot)
                
                old_d1 = dist_func(points[i-1], points[i])
                
                if j < n:
                    old_d2 = dist_func(points[j-1], points[j])
                    new_d1 = dist_func(points[i-1], points[j-1])
                    new_d2 = dist_func(points[i], points[j])
                    
                    old_dist = old_d1 + old_d2
                    new_dist = new_d1 + new_d2
                else:
                    # If j == n, there is no edge leaving j-1 because it's the last stop.
                    # Wait, if we swap i to j-1, the segment from i to j-1 is reversed.
                    # The edge from i-1 to i is replaced by i-1 to j-1.
                    # There is no edge leaving j-1 to j (because j=n is out of bounds).
                    old_dist = old_d1
                    new_dist = dist_func(points[i-1], points[j-1])

                # Use a small epsilon to avoid floating point loops on effectively equal distances
                epsilon = 1e-6
                if new_dist < old_dist - epsilon:
                    # Perform the swap on points
                    points[i:j] = reversed(points[i:j])
                    # Perform the swap on best_route (offset by 1 because points has start_point at 0)
                    best_route[i-1:j-1] = reversed(best_route[i-1:j-1])
                    improved = True
                    break
            if improved:
                break
                
    final_dist = _calculate_route_distance(start_point, best_route, dist_func)
    return best_route, final_dist
