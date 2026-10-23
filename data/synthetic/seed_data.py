import sys
import os
import argparse

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.database.connection import SessionLocal, engine as default_engine
from app.database.base import Base
from app.models.user import User
from app.models.delivery_agent import DeliveryAgent
from app.models.enums import UserRole
from app.auth.security import hash_password
from app.config import settings


def seed_database(target_engine=None):
    use_engine = target_engine or default_engine
    print(f"Seeding synthetic prototype data using engine: {use_engine.url}...")

    Base.metadata.create_all(bind=use_engine)

    from sqlalchemy.orm import sessionmaker
    SeederSession = sessionmaker(autocommit=False, autoflush=False, bind=use_engine)
    db: Session = SeederSession()

    try:
        # 1. Seed Admin
        admin_email = "admin@postal.gov.in"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                name="System Administrator",
                email=admin_email,
                phone="9876500001",
                password_hash=hash_password("Admin@12345"),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            print(f"Created Admin: {admin_email} (Password: Admin@12345)")

        # 2. Seed Delivery Agents
        agents_data = [
            {"name": "Ramesh Delivery Agent", "email": "agent.chennai@postal.gov.in", "phone": "9876500002", "pin": "600001"},
            {"name": "Suresh Delivery Agent", "email": "agent.delhi@postal.gov.in", "phone": "9876500003", "pin": "110001"},
            {"name": "Mahesh Delivery Agent", "email": "agent.mumbai@postal.gov.in", "phone": "9876500004", "pin": "400001"},
        ]

        for ag in agents_data:
            existing_user = db.query(User).filter(User.email == ag["email"]).first()
            if not existing_user:
                u = User(
                    name=ag["name"],
                    email=ag["email"],
                    phone=ag["phone"],
                    password_hash=hash_password("Agent@12345"),
                    role=UserRole.AGENT,
                    is_active=True
                )
                db.add(u)
                db.flush()

                agent_profile = DeliveryAgent(
                    user_id=u.id,
                    service_area=ag["pin"],
                    is_available=True,
                    active_pickup_count=0
                )
                db.add(agent_profile)
                print(f"Created Delivery Agent: {ag['email']} (PIN: {ag['pin']}, Password: Agent@12345)")

        # 3. Seed Demo Citizen
        citizen_email = "citizen.demo@example.com"
        citizen = db.query(User).filter(User.email == citizen_email).first()
        if not citizen:
            citizen = User(
                name="Rahul Sharma",
                email=citizen_email,
                phone="9876543210",
                password_hash=hash_password("Citizen@12345"),
                role=UserRole.CITIZEN,
                is_active=True
            )
            db.add(citizen)
            print(f"Created Demo Citizen: {citizen_email} (Password: Citizen@12345)")

        db.commit()
        print("Seeding completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic data for Module 1")
    parser.add_argument("--sqlite", action="store_true", help="Seed into local SQLite database (smart_postal.db)")
    args = parser.parse_args()

    canonical_sqlite_url = settings.canonicalize_sqlite_path("sqlite:///./smart_postal.db")

    if args.sqlite or "sqlite" in settings.DATABASE_URL:
        print(f"Seeding into canonical development database: {canonical_sqlite_url}")
        sqlite_engine = create_engine(canonical_sqlite_url, connect_args={"check_same_thread": False})
        seed_database(target_engine=sqlite_engine)
    else:
        try:
            seed_database(target_engine=default_engine)
        except Exception as e:
            print("\nNotice: PostgreSQL server not running locally on port 5432.")
            print(f"Seeding into canonical development database: {canonical_sqlite_url}")
            sqlite_engine = create_engine(canonical_sqlite_url, connect_args={"check_same_thread": False})
            seed_database(target_engine=sqlite_engine)
