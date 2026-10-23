import enum


class UserRole(str, enum.Enum):
    CITIZEN = "CITIZEN"
    AGENT = "AGENT"
    ADMIN = "ADMIN"


class ParcelType(str, enum.Enum):
    DOCUMENT = "DOCUMENT"
    SMALL_PARCEL = "SMALL_PARCEL"
    MEDIUM_PARCEL = "MEDIUM_PARCEL"
    LARGE_PARCEL = "LARGE_PARCEL"


class Priority(str, enum.Enum):
    STANDARD = "STANDARD"
    EXPRESS = "EXPRESS"


class PickupStatus(str, enum.Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    PICKED_UP = "PICKED_UP"
    CANCELLED = "CANCELLED"


class ParcelTrackingStatus(str, enum.Enum):
    BOOKED = "BOOKED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    ARRIVED_AT_HUB = "ARRIVED_AT_HUB"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERY_ATTEMPTED = "DELIVERY_ATTEMPTED"
    DELIVERED = "DELIVERED"
