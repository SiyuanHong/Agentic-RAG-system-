import uuid
from datetime import datetime, timezone

from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password


def test_hash_password():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert hashed.startswith("$2")


def test_verify_password_correct():
    hashed = hash_password("correct")
    assert verify_password("correct", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_create_access_token():
    user_id = uuid.UUID("12345678-1234-1234-1234-123456789abc")
    token = create_access_token(user_id, "user@example.com")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == str(user_id)
    assert payload["email"] == "user@example.com"
    assert "exp" in payload


def test_create_access_token_expiry():
    user_id = uuid.UUID("12345678-1234-1234-1234-123456789abc")
    token = create_access_token(user_id, "user@example.com")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = (exp - now).total_seconds()
    # Should be approximately 60 minutes (3600 seconds), allow 10s tolerance
    assert 3500 < diff < 3700
