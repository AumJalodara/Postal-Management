import pytest
from datetime import datetime, timezone, timedelta

from app.services.eta_estimation import calculate_eta
from app.services.route_optimization import RouteResult, RouteStop

# Fixture for a base route result
@pytest.fixture
def base_route_result():
    stops = [
        RouteStop(stop_id="pickup_1", pickup_id=1, pin="111", latitude=10.1, longitude=10.1, stop_type="PICKUP", sequence=1),
        RouteStop(stop_id="pickup_2", pickup_id=2, pin="222", latitude=10.2, longitude=10.2, stop_type="PICKUP", sequence=2),
    ]
    unresolved_stops = [
        RouteStop(stop_id="pickup_3", pickup_id=3, pin="333", latitude=None, longitude=None, stop_type="PICKUP", sequence=-1),
    ]
    return RouteResult(
        agent_id=1,
        start_location={"pin": "AGENT_PIN", "latitude": 10.0, "longitude": 10.0},
        stops=stops,
        total_distance_km=15.0, # 15km
        initial_distance_km=20.0,
        optimized_distance_km=15.0,
        improvement_percent=25.0,
        algorithm="Haversine + Greedy Nearest Neighbor + 2-opt",
        unresolved_stops=unresolved_stops
    )

def test_eta_basic_calculation(base_route_result):
    # dist = 15.0 km
    # speed = 30 km/h -> travel = 30 mins
    # 2 routable stops, 1 unresolved
    # service time = 5 mins/stop -> 10 mins
    # buffer = 10 mins
    # total = 30 + 10 + 10 = 50 mins
    eta = calculate_eta(base_route_result, speed_kmph=30.0, service_time_per_stop=5.0, buffer_minutes=10.0)
    
    assert eta.travel_time_minutes == 30.0
    assert eta.service_time_minutes == 10.0
    assert eta.buffer_minutes == 10.0
    assert eta.total_eta_minutes == 50.0
    
    assert eta.routable_stop_count == 2
    assert eta.unresolved_stop_count == 1
    assert "pickup_3" in eta.unresolved_stop_ids

def test_eta_zero_distance_and_empty_route(base_route_result):
    # Make route completely empty
    base_route_result.stops = []
    base_route_result.optimized_distance_km = 0.0
    
    # Even if buffer is 10, an empty route should return 0 ETA
    eta = calculate_eta(base_route_result, speed_kmph=30.0, service_time_per_stop=5.0, buffer_minutes=10.0)
    
    assert eta.travel_time_minutes == 0.0
    assert eta.service_time_minutes == 0.0
    assert eta.buffer_minutes == 0.0
    assert eta.total_eta_minutes == 0.0

def test_eta_zero_distance_with_stops(base_route_result):
    # Route distance 0 but stops exist (e.g. all pickups at agent's location)
    base_route_result.optimized_distance_km = 0.0
    
    eta = calculate_eta(base_route_result, speed_kmph=30.0, service_time_per_stop=5.0, buffer_minutes=10.0)
    
    assert eta.travel_time_minutes == 0.0
    assert eta.service_time_minutes == 10.0
    assert eta.buffer_minutes == 10.0
    assert eta.total_eta_minutes == 20.0

def test_eta_start_time_timezone_preservation(base_route_result):
    # total ETA = 50 mins
    # Naive dt
    naive_start = datetime(2026, 1, 1, 10, 0)
    eta_naive = calculate_eta(base_route_result, start_time=naive_start, speed_kmph=30.0, service_time_per_stop=5.0, buffer_minutes=10.0)
    assert eta_naive.estimated_completion_time == naive_start + timedelta(minutes=50)
    assert eta_naive.estimated_completion_time.tzinfo is None
    assert eta_naive.assumptions["timezone_aware"] is False

    # Aware dt
    aware_start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    eta_aware = calculate_eta(base_route_result, start_time=aware_start, speed_kmph=30.0, service_time_per_stop=5.0, buffer_minutes=10.0)
    assert eta_aware.estimated_completion_time == aware_start + timedelta(minutes=50)
    assert eta_aware.estimated_completion_time.tzinfo is not None
    assert eta_aware.assumptions["timezone_aware"] is True

def test_eta_configuration_validation(base_route_result):
    with pytest.raises(ValueError, match="Average speed must be greater than 0"):
        calculate_eta(base_route_result, speed_kmph=0.0)
        
    with pytest.raises(ValueError, match="Average speed must be greater than 0"):
        calculate_eta(base_route_result, speed_kmph=-10.0)
        
    with pytest.raises(ValueError, match="Service time must be non-negative"):
        calculate_eta(base_route_result, service_time_per_stop=-1.0)
        
    with pytest.raises(ValueError, match="Buffer must be non-negative"):
        calculate_eta(base_route_result, buffer_minutes=-5.0)

def test_eta_determinism(base_route_result):
    eta1 = calculate_eta(base_route_result, speed_kmph=30.0, service_time_per_stop=5.0, buffer_minutes=10.0)
    eta2 = calculate_eta(base_route_result, speed_kmph=30.0, service_time_per_stop=5.0, buffer_minutes=10.0)
    eta3 = calculate_eta(base_route_result, speed_kmph=30.0, service_time_per_stop=5.0, buffer_minutes=10.0)
    
    assert eta1 == eta2
    assert eta2 == eta3


# Integration test with route optimization
def test_eta_route_integration(monkeypatch):
    from app.services.route_optimization import build_optimized_route
    from app.models.pickup import PickupRequest
    from app.models.enums import PickupStatus
    
    locations = {
        "AGENT": {"latitude": 10.0, "longitude": 10.0},
        "P1": {"latitude": 10.1, "longitude": 10.1},
    }
    class MockService:
        def get_location_for_pin(self, pin: str):
            return locations.get(pin)
            
    import app.services.route_optimization as ro
    monkeypatch.setattr(ro, "postal_location_service", MockService())
    
    p = PickupRequest(id=1, pickup_pin="P1", status=PickupStatus.ASSIGNED)
    route_result = build_optimized_route(1, "AGENT", [p])
    
    eta = calculate_eta(route_result, speed_kmph=30.0, service_time_per_stop=5.0, buffer_minutes=10.0)
    
    assert eta.agent_id == 1
    assert eta.routable_stop_count == 1
    assert eta.unresolved_stop_count == 0
    
    assert eta.travel_time_minutes > 0
    assert eta.service_time_minutes == 5.0
    assert eta.buffer_minutes == 10.0
    assert eta.total_eta_minutes == eta.travel_time_minutes + 15.0
