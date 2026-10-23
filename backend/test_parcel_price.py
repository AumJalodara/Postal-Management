import os
import sys

# Ensure backend is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import SessionLocal
from app.schemas.parcel import ParcelCreate
from app.models.enums import ParcelType, Priority
from app.services.parcel_service import create_parcel
from app.models.user import User
from app.models.enums import UserRole

db = SessionLocal()

try:
    # 1. Get an existing user
    user = db.query(User).first()
    if not user:
        print("No user found in database to test with.")
        sys.exit(1)

    # 2. Create parcel data with price
    parcel_in = ParcelCreate(
        receiver_name="John Doe",
        receiver_phone="9876543210",
        destination_address="123 Test St",
        destination_city="Test City",
        destination_state="Test State",
        destination_pin="110001",
        weight=2.5,
        parcel_type=ParcelType.SMALL_PARCEL,
        priority=Priority.STANDARD,
        price=150.75
    )

    # 3. Call service function
    parcel = create_parcel(db=db, sender_id=user.id, parcel_in=parcel_in)

    print(f"SUCCESS: Parcel created! ID={parcel.id}, Tracking={parcel.tracking_id}, Price={parcel.price}")

except Exception as e:
    print(f"FAILED: {e}")
finally:
    # Clean up (Optional, but good for tests)
    if 'parcel' in locals():
        db.delete(parcel)
        db.commit()
    db.close()
