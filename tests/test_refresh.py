from datetime import date

# --- Helpers ---
def register_and_login_employee(client, email="alice@example.com", password="secret123"):
    """Register an employee and login, returning (employee, tokens)."""
    emp = client.post("/auth/register", json={
        "name": "Alice",
        "email": email,
        "department": "Engineering",
        "joining_date": str(date.today()),
        "password": password
    }).json()

    response = client.post("/auth/token", data={
        "username": email,
        "password": password
    })
    assert response.status_code == 200
    tokens = response.json()
    return emp, tokens


# --- TESTS ---

def test_login_returns_access_and_refresh_tokens(client):
    _, tokens = register_and_login_employee(client)
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


def test_refresh_with_valid_token(client):
    _, tokens = register_and_login_employee(client)
    refresh_token = tokens["refresh_token"]

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # ensure a new refresh token is issued (rotation enabled)
    assert data["refresh_token"] != refresh_token


def test_refresh_with_invalid_token(client):
    response = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


def test_logout_revokes_refresh_token(client):
    _, tokens = register_and_login_employee(client)
    refresh_token = tokens["refresh_token"]

    # logout
    resp = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Logged out successfully"

    # try refreshing with the same token → must fail
    resp2 = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp2.status_code == 401
    assert resp2.json()["detail"] == "Invalid or expired refresh token"


def test_cannot_logout_with_invalid_token(client):
    resp = client.post("/auth/logout", json={"refresh_token": "fake-token"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid refresh token"




def test_refresh_after_access_token_expired(client, monkeypatch):
    # Force access tokens to expire immediately
    monkeypatch.setattr("app.config.settings.ACCESS_TOKEN_EXPIRE_MINUTES", -1)

    emp, tokens = register_and_login_employee(client)
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # Try to use expired access token → should fail
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = client.get(f"/employees/{emp['id']}", headers=headers)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid Token"

    # Restore config to normal so refreshed tokens are valid
    monkeypatch.setattr("app.config.settings.ACCESS_TOKEN_EXPIRE_MINUTES", 15)

    # Use refresh token to get new access token
    refresh_resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens

    # New access token should now work
    new_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    resp2 = client.get(f"/employees/{emp['id']}", headers=new_headers)
    assert resp2.status_code == 200
    assert resp2.json()["email"] == "alice@example.com"
