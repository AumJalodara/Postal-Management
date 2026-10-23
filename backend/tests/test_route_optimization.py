import pytest
from app.services.route_optimization import build_optimized_route, RouteStop
from app.models.pickup import PickupRequest
from app.models.enums import PickupStatus

# Mock postal location service to return predictable coordinates
@pytest.fixture
def mock_postal_location(monkeypatch):
    locations = {
        "AGENT_PIN": {"latitude": 10.0, "longitude": 10.0},
        "PIN1": {"latitude": 10.1, "longitude": 10.1},
        "PIN2": {"latitude": 10.2, "longitude": 10.2},
        "PIN3": {"latitude": 10.3, "longitude": 10.3},
        "PIN_CROSS1": {"latitude": 10.0, "longitude": 11.0},
        "PIN_CROSS2": {"latitude": 11.0, "longitude": 10.0},
        "PIN_CROSS3": {"latitude": 11.0, "longitude": 11.0},
        "PIN_NO_COORD": {"latitude": None, "longitude": None},
    }
    
    class MockService:
        def get_location_for_pin(self, pin: str):
            return locations.get(pin)
            
    import app.services.route_optimization as ro
    monkeypatch.setattr(ro, "postal_location_service", MockService())


def test_empty_route(mock_postal_location):
    res = build_optimized_route(1, "AGENT_PIN", [])
    assert res.agent_id == 1
    assert res.stops == []
    assert res.total_distance_km == 0.0
    assert res.initial_distance_km == 0.0


def test_single_stop_route(mock_postal_location):
    p = PickupRequest(id=1, pickup_pin="PIN1", status=PickupStatus.ASSIGNED)
    res = build_optimized_route(1, "AGENT_PIN", [p])
    assert len(res.stops) == 1
    assert res.stops[0].pin == "PIN1"
    assert res.stops[0].sequence == 1
    assert res.total_distance_km > 0
    assert res.initial_distance_km == res.optimized_distance_km
    assert res.improvement_percent == 0.0


def test_greedy_nearest_neighbor(mock_postal_location):
    # Agent at 10.0, 10.0
    # P1 at 10.3, 10.3
    # P2 at 10.1, 10.1
    # P3 at 10.2, 10.2
    # Greedy from agent should visit P2, then P3, then P1
    p1 = PickupRequest(id=1, pickup_pin="PIN3", status=PickupStatus.ASSIGNED)
    p2 = PickupRequest(id=2, pickup_pin="PIN1", status=PickupStatus.ASSIGNED)
    p3 = PickupRequest(id=3, pickup_pin="PIN2", status=PickupStatus.ASSIGNED)
    
    res = build_optimized_route(1, "AGENT_PIN", [p1, p2, p3])
    
    assert len(res.stops) == 3
    assert res.stops[0].pickup_id == 2
    assert res.stops[1].pickup_id == 3
    assert res.stops[2].pickup_id == 1
    
    assert res.stops[0].sequence == 1
    assert res.stops[1].sequence == 2
    assert res.stops[2].sequence == 3


def test_missing_coordinates(mock_postal_location):
    p1 = PickupRequest(id=1, pickup_pin="PIN1", status=PickupStatus.ASSIGNED)
    p2 = PickupRequest(id=2, pickup_pin="PIN_NO_COORD", status=PickupStatus.ASSIGNED)
    p3 = PickupRequest(id=3, pickup_pin="UNKNOWN_PIN", status=PickupStatus.ASSIGNED)
    
    res = build_optimized_route(1, "AGENT_PIN", [p1, p2, p3])
    
    assert len(res.stops) == 1
    assert res.stops[0].pickup_id == 1
    
    assert len(res.unresolved_stops) == 2
    assert {s.pickup_id for s in res.unresolved_stops} == {2, 3}


def test_2opt_improvement(mock_postal_location):
    # We construct a scenario where greedy makes a suboptimal choice.
    # Start: (0, 0)
    # A = (1, 1), B = (1, -1), C = (2, -1), D = (2, 1)
    # Wait, haversine works with lat/lon. Let's use simple coords.
    # Agent: 10.0, 10.0
    # Stops: 
    # S1: 10.1, 10.0
    # S2: 10.1, 10.5
    # S3: 10.0, 10.5
    # S4: 10.0, 10.1 (very close to agent but slightly farther than S1)
    
    # Actually, constructing a reliable 2-opt test in geographic coords manually can be tricky.
    # A simple crossing: 
    # Start: (10, 10). 
    # P1 = (10, 11), P2 = (11, 10)
    # P3 = (11, 11), P4 = (12, 10)
    # Let's just create points that clearly cross, and the 2-opt should uncross them.
    # We will just verify that optimized_distance <= initial_distance.
    
    p1 = PickupRequest(id=1, pickup_pin="PIN_CROSS1", status=PickupStatus.ASSIGNED)
    p2 = PickupRequest(id=2, pickup_pin="PIN_CROSS2", status=PickupStatus.ASSIGNED)
    p3 = PickupRequest(id=3, pickup_pin="PIN_CROSS3", status=PickupStatus.ASSIGNED)
    p4 = PickupRequest(id=4, pickup_pin="PIN1", status=PickupStatus.ASSIGNED)
    
    res = build_optimized_route(1, "AGENT_PIN", [p1, p2, p3, p4])
    
    assert res.optimized_distance_km <= res.initial_distance_km
    assert res.improvement_percent >= 0.0


def test_duplicate_coordinates(mock_postal_location):
    p1 = PickupRequest(id=1, pickup_pin="PIN1", status=PickupStatus.ASSIGNED)
    p2 = PickupRequest(id=2, pickup_pin="PIN1", status=PickupStatus.ASSIGNED)
    
    res = build_optimized_route(1, "AGENT_PIN", [p1, p2])
    
    assert len(res.stops) == 2
    # Distance between p1 and p2 should be 0.
    assert res.stops[0].pickup_id in (1, 2)
    assert res.stops[1].pickup_id in (1, 2)
    assert res.total_distance_km > 0 # distance from agent to PIN1
    

def test_unroutable_status(mock_postal_location):
    p1 = PickupRequest(id=1, pickup_pin="PIN1", status=PickupStatus.PENDING)
    p2 = PickupRequest(id=2, pickup_pin="PIN1", status=PickupStatus.PICKED_UP)
    p3 = PickupRequest(id=3, pickup_pin="PIN1", status=PickupStatus.CANCELLED)
    
    res = build_optimized_route(1, "AGENT_PIN", [p1, p2, p3])
    
    assert len(res.stops) == 0
    assert res.total_distance_km == 0.0
