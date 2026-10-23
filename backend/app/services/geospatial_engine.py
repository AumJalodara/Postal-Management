import math
from typing import Optional, Tuple

# Earth's mean radius in kilometers
EARTH_RADIUS_KM = 6371.0


class InvalidCoordinateError(ValueError):
    """Exception raised for invalid geographic coordinates."""
    pass


def validate_coordinate(latitude: float, longitude: float) -> Tuple[float, float]:
    """
    Validates a geographic coordinate pair.
    
    Requirements:
    - -90 <= latitude <= 90
    - -180 <= longitude <= 180
    - Reject NaN and Infinity
    - Do not silently clamp or modify invalid values.
    
    Returns:
        Tuple of (latitude, longitude) if valid.
        
    Raises:
        InvalidCoordinateError if validation fails.
    """
    if latitude is None or longitude is None:
        raise InvalidCoordinateError("Latitude and longitude cannot be None.")

    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        raise InvalidCoordinateError(f"Coordinates must be numeric. Got lat={latitude}, lon={longitude}")

    if math.isnan(lat) or math.isnan(lon):
        raise InvalidCoordinateError("Coordinates cannot be NaN.")

    if math.isinf(lat) or math.isinf(lon):
        raise InvalidCoordinateError("Coordinates cannot be Infinity.")

    if not (-90.0 <= lat <= 90.0):
        raise InvalidCoordinateError(f"Latitude must be between -90 and 90. Got {lat}")

    if not (-180.0 <= lon <= 180.0):
        raise InvalidCoordinateError(f"Longitude must be between -180 and 180. Got {lon}")

    return lat, lon


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle geographic distance between two points
    on the Earth's surface using the Haversine formula.

    Inputs:
    - lat1, lon1: Coordinates of point 1
    - lat2, lon2: Coordinates of point 2

    Returns:
    - Distance in kilometers.
    
    Raises:
    - InvalidCoordinateError if any coordinate is invalid.
    """
    # 1. Validate inputs
    lat1, lon1 = validate_coordinate(lat1, lon1)
    lat2, lon2 = validate_coordinate(lat2, lon2)

    # 2. Convert latitude and longitude from degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # 3. Apply Haversine formula
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2

    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance_km = EARTH_RADIUS_KM * c

    # 4. Enforce non-negative distance (handle potential tiny negative floats from precision issues)
    return max(0.0, distance_km)

