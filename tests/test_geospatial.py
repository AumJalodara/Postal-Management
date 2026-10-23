import pytest
import math
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.geospatial_engine import haversine_distance, validate_coordinate, InvalidCoordinateError

class TestGeospatialEngine:
    # --- Validation Tests ---
    
    def test_valid_coordinates(self):
        lat, lon = validate_coordinate(12.34, 56.78)
        assert lat == 12.34
        assert lon == 56.78
        
        # Test boundaries
        assert validate_coordinate(90.0, 180.0) == (90.0, 180.0)
        assert validate_coordinate(-90.0, -180.0) == (-90.0, -180.0)
        assert validate_coordinate(0.0, 0.0) == (0.0, 0.0)

    def test_invalid_latitude_boundary(self):
        with pytest.raises(InvalidCoordinateError, match="Latitude must be between"):
            validate_coordinate(90.1, 0)
            
        with pytest.raises(InvalidCoordinateError, match="Latitude must be between"):
            validate_coordinate(-90.1, 0)

    def test_invalid_longitude_boundary(self):
        with pytest.raises(InvalidCoordinateError, match="Longitude must be between"):
            validate_coordinate(0, 180.1)
            
        with pytest.raises(InvalidCoordinateError, match="Longitude must be between"):
            validate_coordinate(0, -180.1)

    def test_non_numeric_coordinates(self):
        with pytest.raises(InvalidCoordinateError, match="Coordinates must be numeric"):
            validate_coordinate("invalid", 0)
            
        with pytest.raises(InvalidCoordinateError, match="Coordinates must be numeric"):
            validate_coordinate(0, "invalid")

    def test_missing_coordinates(self):
        with pytest.raises(InvalidCoordinateError, match="cannot be None"):
            validate_coordinate(None, 0)
            
        with pytest.raises(InvalidCoordinateError, match="cannot be None"):
            validate_coordinate(0, None)
            
        with pytest.raises(InvalidCoordinateError, match="cannot be None"):
            validate_coordinate(None, None)

    def test_nan_infinity_coordinates(self):
        with pytest.raises(InvalidCoordinateError, match="cannot be NaN"):
            validate_coordinate(float('nan'), 0)
            
        with pytest.raises(InvalidCoordinateError, match="cannot be Infinity"):
            validate_coordinate(float('inf'), 0)
            
        with pytest.raises(InvalidCoordinateError, match="cannot be Infinity"):
            validate_coordinate(0, float('-inf'))

    # --- Distance Calculation Tests ---

    def test_distance_identity(self):
        # distance(A, A) == 0
        dist = haversine_distance(12.34, 56.78, 12.34, 56.78)
        assert dist == 0.0

    def test_distance_symmetry(self):
        # distance(A, B) == distance(B, A)
        dist_ab = haversine_distance(12.34, 56.78, -12.34, -56.78)
        dist_ba = haversine_distance(-12.34, -56.78, 12.34, 56.78)
        assert math.isclose(dist_ab, dist_ba, rel_tol=1e-9)

    def test_distance_non_negative(self):
        # distance(A, B) >= 0
        dist = haversine_distance(12.34, 56.78, -12.34, -56.78)
        assert dist >= 0.0

    def test_known_geographic_reference(self):
        # New Delhi: 28.6139, 77.2090
        # Mumbai: 19.0760, 72.8777
        # Expected distance is ~1148 km
        dist = haversine_distance(28.6139, 77.2090, 19.0760, 72.8777)
        # Check if it falls within an acceptable range (e.g. 1140 to 1160 km depending on Earth radius constants)
        assert 1140 <= dist <= 1160
        # Given EARTH_RADIUS_KM = 6371.0, the precise math yields ~1148.06 km
        assert math.isclose(dist, 1148.06, abs_tol=1.0)

    def test_hemisphere_cross(self):
        # Test coordinates in different hemispheres
        # Point 1: 45.0 N, 45.0 W
        # Point 2: 45.0 S, 45.0 E
        dist = haversine_distance(45.0, -45.0, -45.0, 45.0)
        assert dist > 0.0

    def test_antipodal_points(self):
        # Maximum possible distance is half the circumference: pi * R
        # 6371 * pi ≈ 20015.08 km
        dist = haversine_distance(90.0, 0.0, -90.0, 0.0)
        assert math.isclose(dist, math.pi * 6371.0, rel_tol=1e-5)
        
        dist2 = haversine_distance(0.0, 180.0, 0.0, 0.0)
        assert math.isclose(dist2, math.pi * 6371.0, rel_tol=1e-5)
