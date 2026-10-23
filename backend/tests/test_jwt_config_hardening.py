"""
Regression tests for Finding SEC-001: JWT Secret Configuration Hardening.
Verifies:
1. Development mode permits isolated dev/test secrets.
2. Production mode rejects missing, blank, short, and default placeholder secrets.
3. Production mode accepts valid high-entropy secrets >= 32 characters.
4. Error messages are safe and non-sensitive (no leaked secrets).
"""

import pytest
from pydantic import ValidationError
from app.config import Settings


def test_dev_mode_allows_documented_dev_secret():
    """In development/test mode, the default dev secret is permitted for developer convenience."""
    s = Settings(
        APPLICATION_ENV="development",
        JWT_SECRET="super-secret-dev-key-change-in-production-min32chars"
    )
    assert not s.is_production
    assert s.JWT_SECRET == "super-secret-dev-key-change-in-production-min32chars"


def test_production_rejects_default_placeholder_secret():
    """In production mode, the default placeholder secret must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APPLICATION_ENV="production",
            JWT_SECRET="super-secret-dev-key-change-in-production-min32chars"
        )
    err_msg = exc_info.value.errors()[0]["msg"]
    assert "Known development placeholder detected" in err_msg
    # Confirm no secret value is exposed in the error message
    assert "super-secret-dev-key" not in err_msg


def test_production_rejects_short_secret():
    """In production mode, secrets under 32 characters (256-bit entropy) must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APPLICATION_ENV="production",
            JWT_SECRET="short-key-12345"
        )
    err_msg = exc_info.value.errors()[0]["msg"]
    assert "below the minimum requirement of 32 characters" in err_msg
    assert "short-key-12345" not in err_msg


def test_production_rejects_empty_secret():
    """In production mode, empty or whitespace-only secrets must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APPLICATION_ENV="production",
            JWT_SECRET=""
        )
    err_msg = exc_info.value.errors()[0]["msg"]
    assert "JWT_SECRET must be set in production" in err_msg


def test_production_accepts_valid_high_entropy_secret():
    """In production mode, a cryptographically secure 32+ character random key is accepted."""
    secure_key = "a8f3b2c1d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef"
    s = Settings(
        APPLICATION_ENV="production",
        JWT_SECRET=secure_key
    )
    assert s.is_production
    assert s.JWT_SECRET == secure_key
