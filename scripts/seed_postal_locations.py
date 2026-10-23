import os
import sys
import csv
import logging
from sqlalchemy.orm import Session

# Set up paths to access backend models
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend'))
if backend_path not in sys.path:
    sys.path.append(backend_path)

from app.database.connection import SessionLocal, engine
from app.models.tracking import PostalLocation
from app.database.base import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/postal_reference/processed/postal_reference_cleaned.csv'))

def seed_postal_locations():
    if not os.path.exists(CSV_PATH):
        logger.error(f"Dataset not found at: {CSV_PATH}")
        return

    # Ensure tables are recreated with new schema
    logger.info("Initializing database schema for Postal Locations...")
    PostalLocation.__table__.drop(bind=engine, checkfirst=True)
    PostalLocation.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    count = db.query(PostalLocation).count()
    if count > 0:
        logger.info(f"Found {count} existing records. Clearing old data...")
        db.query(PostalLocation).delete()
        db.commit()

    logger.info(f"Reading from dataset: {CSV_PATH}")
    
    batch_size = 10000
    batch = []
    total_inserted = 0
    
    with open(CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            batch.append({
                "pincode": row.get("pincode", ""),
                "office_name": row.get("officename", ""),
                "office_type": row.get("officetype", ""),
                "district": row.get("district", ""),
                "state": row.get("statename", ""),
                "region": row.get("regionname", ""),
                "division": row.get("divisionname", ""),
                "circle": row.get("circlename", ""),
                "delivery_status": row.get("delivery", ""),
                "latitude": row.get("latitude", "") if row.get("latitude") else None,
                "longitude": row.get("longitude", "") if row.get("longitude") else None,
            })
            
            if len(batch) >= batch_size:
                db.bulk_insert_mappings(PostalLocation, batch)
                db.commit()
                total_inserted += len(batch)
                logger.info(f"Inserted {total_inserted} records...")
                batch = []
                
        # Insert any remaining rows
        if batch:
            db.bulk_insert_mappings(PostalLocation, batch)
            db.commit()
            total_inserted += len(batch)
            logger.info(f"Inserted {total_inserted} records...")

    db.close()
    logger.info("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_postal_locations()
