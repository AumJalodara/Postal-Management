import logging
import threading
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

logger = logging.getLogger(__name__)

is_sqlite = "sqlite" in settings.DATABASE_URL

connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_sqlite_seq_lock = threading.Lock()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_next_tracking_sequence(db: Session) -> int:
    """
    Concurrency-safe sequence number generator.
    In PostgreSQL, uses the native database sequence postal_tracking_seq.
    In SQLite (used for testing), uses a thread-safe mutex and persistent counter.
    """
    bind = db.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        result = db.execute(text("SELECT nextval('postal_tracking_seq')"))
        return int(result.scalar_one())
    else:
        # Thread-safe SQLite sequence emulation for concurrent tests
        with _sqlite_seq_lock:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS tracking_sequence_emulator (
                    id INTEGER PRIMARY KEY,
                    val INTEGER NOT NULL
                )
            """))
            row = db.execute(text("SELECT val FROM tracking_sequence_emulator WHERE id = 1")).fetchone()
            if row is None:
                db.execute(text("INSERT INTO tracking_sequence_emulator (id, val) VALUES (1, 1)"))
                db.commit()
                val = 1
            else:
                current_val = row[0]
                val = current_val + 1
                db.execute(
                    text("UPDATE tracking_sequence_emulator SET val = :val WHERE id = 1"),
                    {"val": val}
                )
                db.commit()
            return val

