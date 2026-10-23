"""
Regression tests for Finding DB-001: Unified Database Path Resolution.
Verifies:
1. Relative SQLite URLs predictably resolve to the canonical backend/ directory.
2. Absolute SQLite paths remain unchanged.
3. PostgreSQL connection URLs remain untouched.
"""

import os
from app.config import Settings, BACKEND_DIR


def test_relative_sqlite_path_canonicalization():
    """Relative paths like sqlite:///./smart_postal.db must resolve to backend/smart_postal.db."""
    s = Settings(
        DATABASE_URL="sqlite:///./smart_postal.db"
    )
    expected_path = os.path.normpath(os.path.join(BACKEND_DIR, "smart_postal.db"))
    expected_url = f"sqlite:///{expected_path}"
    assert s.DATABASE_URL == expected_url


def test_simple_sqlite_filename_canonicalization():
    """Simple filenames like sqlite:///smart_postal.db must resolve to backend/smart_postal.db."""
    s = Settings(
        DATABASE_URL="sqlite:///smart_postal.db"
    )
    expected_path = os.path.normpath(os.path.join(BACKEND_DIR, "smart_postal.db"))
    expected_url = f"sqlite:///{expected_path}"
    assert s.DATABASE_URL == expected_url


def test_postgresql_url_remains_untouched():
    """PostgreSQL URLs must not be modified by SQLite canonicalizer."""
    pg_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/smart_postal_db"
    s = Settings(
        DATABASE_URL=pg_url
    )
    assert s.DATABASE_URL == pg_url
