import os
import sys
import tempfile
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.config import settings
from app.database.base import Base
from app.database.connection import get_db
from app.models.user import User
from app.models.delivery_agent import DeliveryAgent
from app.models.enums import UserRole
from app.auth.security import hash_password, create_access_token

TEMP_DB_FILE = os.path.join(tempfile.gettempdir(), "smart_postal_test.db")
if os.path.exists(TEMP_DB_FILE):
    try:
        os.remove(TEMP_DB_FILE)
    except Exception:
        pass

SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEMP_DB_FILE}"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30}
)

@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=10000")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def init_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists(TEMP_DB_FILE):
        try:
            os.remove(TEMP_DB_FILE)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def clean_tables_each_test():
    """Ensure clean table state for complete test isolation."""
    yield
    with test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seed_users(db):
    # Citizen 1
    c1 = User(
        name="Rahul Kumar",
        email="rahul.kumar@example.com",
        phone="9876543210",
        password_hash=hash_password("Password@123"),
        role=UserRole.CITIZEN,
        is_active=True
    )
    # Citizen 2
    c2 = User(
        name="Priya Sharma",
        email="priya.sharma@example.com",
        phone="9876543211",
        password_hash=hash_password("Password@123"),
        role=UserRole.CITIZEN,
        is_active=True
    )
    # Agent 1 (Assigned to 600001)
    ag1_user = User(
        name="Agent Chennai",
        email="agent1@postal.gov.in",
        phone="9876543212",
        password_hash=hash_password("Password@123"),
        role=UserRole.AGENT,
        is_active=True
    )
    # Agent 2 (Assigned to 600001)
    ag2_user = User(
        name="Agent Chennai Two",
        email="agent2@postal.gov.in",
        phone="9876543213",
        password_hash=hash_password("Password@123"),
        role=UserRole.AGENT,
        is_active=True
    )
    # Admin
    admin = User(
        name="Admin User",
        email="admin@postal.gov.in",
        phone="9876543214",
        password_hash=hash_password("Password@123"),
        role=UserRole.ADMIN,
        is_active=True
    )

    db.add_all([c1, c2, ag1_user, ag2_user, admin])
    db.commit()

    ag1 = DeliveryAgent(
        user_id=ag1_user.id,
        service_area="600001",
        is_available=True,
        active_pickup_count=0
    )
    ag2 = DeliveryAgent(
        user_id=ag2_user.id,
        service_area="600001",
        is_available=True,
        active_pickup_count=1
    )
    db.add_all([ag1, ag2])
    db.commit()

    return {
        "citizen1": c1,
        "citizen2": c2,
        "agent1_user": ag1_user,
        "agent1": ag1,
        "agent2_user": ag2_user,
        "agent2": ag2,
        "admin": admin
    }


def auth_header_for_user(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id), "role": user.role.value, "email": user.email})
    return {"Authorization": f"Bearer {token}"}
