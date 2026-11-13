import pytest
from app.models.enums import UserRole


def test_register_citizen_success(client):
    payload = {
        "name": "Ananya Roy",
        "email": "ananya.roy@example.com",
        "phone": "9876512345",
        "password": "Password@123"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "ananya.roy@example.com"
    assert data["data"]["role"] == "CITIZEN"


def test_register_duplicate_email(client):
    payload = {
        "name": "Ananya Roy",
        "email": "ananya.duplicate@example.com",
        "phone": "9876512345",
        "password": "Password@123"
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409
    assert r2.json()["success"] is False
    assert r2.json()["error"]["code"] == "EMAIL_EXISTS"


def test_register_ignores_client_role(client):
    # Attempting to supply role="ADMIN" should not escalate privileges
    payload = {
        "name": "Hacker User",
        "email": "hacker@example.com",
        "phone": "9876512346",
        "password": "Password@123",
        "role": "ADMIN"  # Client trying to pass role
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["data"]["role"] == "CITIZEN"


def test_login_success_and_invalid_password(client):
    # Register first
    client.post("/api/v1/auth/register", json={
        "name": "Vikram Singh",
        "email": "vikram.singh@example.com",
        "phone": "9876512347",
        "password": "CorrectPassword1"
    })

    # Wrong password
    bad_login = client.post("/api/v1/auth/login", json={
        "email": "vikram.singh@example.com",
        "password": "WrongPassword"
    })
    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "INVALID_CREDENTIALS"

    # Correct password
    good_login = client.post("/api/v1/auth/login", json={
        "email": "vikram.singh@example.com",
        "password": "CorrectPassword1"
    })
    assert good_login.status_code == 200
    assert good_login.json()["success"] is True
    token = good_login.json()["data"]["access_token"]
    assert token is not None

    # Verify /auth/me with token
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["email"] == "vikram.singh@example.com"


def test_auth_missing_or_invalid_token(client):
    # Missing token
    r1 = client.get("/api/v1/auth/me")
    assert r1.status_code == 401
    assert r1.json()["error"]["code"] == "MISSING_TOKEN"

    # Invalid token
    r2 = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.jwt.string"})
    assert r2.status_code == 401
    assert r2.json()["error"]["code"] == "INVALID_TOKEN"


def test_update_user_profile(client, seed_users):
    # Login with seeded citizen
    email = "rahul.kumar@example.com"
    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password@123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Successful update of name and phone
    update_res = client.put("/api/v1/auth/me", headers=headers, json={
        "name": "Rahul Updated",
        "phone": "9876599999",
        "role": "ADMIN",  # Should be ignored / protected
        "email": "hacked@example.com"  # Should be ignored / protected
    })
    assert update_res.status_code == 200
    updated_data = update_res.json()["data"]
    assert updated_data["name"] == "Rahul Updated"
    assert updated_data["phone"] == "9876599999"
    assert updated_data["email"] == email  # Protected
    assert updated_data["role"] == "CITIZEN"  # Protected

    # Verify persistence via GET /me
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["name"] == "Rahul Updated"
    assert me_res.json()["data"]["phone"] == "9876599999"


def test_logout_and_jwt_revocation(client, seed_users):
    # Login with admin
    email = "admin@postal.gov.in"
    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password@123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify access before logout
    before_res = client.get("/api/v1/auth/me", headers=headers)
    assert before_res.status_code == 200

    # Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True

    # Attempt to access protected endpoint with the revoked token
    after_res = client.get("/api/v1/auth/me", headers=headers)
    assert after_res.status_code == 401
    assert after_res.json()["error"]["code"] == "TOKEN_REVOKED"

    # Login again produces a fresh valid token
    new_login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password@123"
    })
    assert new_login_res.status_code == 200
    new_token = new_login_res.json()["data"]["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}
    new_access_res = client.get("/api/v1/auth/me", headers=new_headers)
    assert new_access_res.status_code == 200
    assert new_access_res.json()["data"]["email"] == email
