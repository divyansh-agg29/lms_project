from app import auth


def test_register_employee(client):
    response = client.post("/auth/register",json={
        "name": "Alice",
        "email": "alice@example.com",
        "department": "Engineering",
        "joining_date": "2025-01-01",
        "password": "password123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data['email'] == "alice@example.com"
    assert data['role'] == "employee"
    assert "id" in data


def test_register_duplicate_email(client):
    client.post("/auth/register", json={
        "name": "Bob",
        "email": "bob@example.com",
        "department": "HR",
        "joining_date": "2025-01-01",
        "password": "password123"
    })

    response = client.post("/auth/register", json={
        "name": "Bob2",
        "email": "bob@example.com",
        "department": "HR",
        "joining_date": "2025-01-02",
        "password": "password456"
    })
    assert response.status_code == 400
    assert response.json()['detail'] == "Email already exist"


def test_register_with_role_field_is_ignored(client):
    response = client.post("/auth/register", json={
        "name": "Charlie",
        "email": "charlie@example.com",
        "department": "Finance",
        "joining_date": "2025-01-01",
        "password": "pass123",
        "role": "manager"   # trying to put role as manager
    })
    assert response.status_code == 201
    data = response.json()
    # API must ignore this and force role=employee
    assert data["role"] == "employee"


def test_login_success(client):
    client.post("/auth/register", json={
        "name": "Diana",
        "email": "diana@example.com",
        "department": "Sales",
        "joining_date": "2025-01-01",
        "password": "mypassword"
    })

    response = client.post("/auth/token", data={
        "username": "diana@example.com",
        "password": "mypassword"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    # Decode token to verify contents
    payload = auth.decode_token(data["access_token"])
    assert payload["sub"] == "diana@example.com"
    assert payload["role"] == "employee"


def test_login_wrong_password(client):
    client.post("/auth/register", json={
        "name": "Eve",
        "email": "eve@example.com",
        "department": "Support",
        "joining_date": "2025-01-01",
        "password": "correctpass"
    })

    response = client.post("/auth/token", data={
        "username": "eve@example.com",
        "password": "wrongpass"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Credentials"


def test_login_nonexistent_email(client):
    response = client.post("/auth/token", data={
        "username": "name@example.com",
        "password": "nopass"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Credentials"


def test_token_expiry(client, monkeypatch):
    # Force tokens to expire immediately
    monkeypatch.setattr("app.config.settings.ACCESS_TOKEN_EXPIRE_MINUTES", -1)

    # Register an employee
    response = client.post("/auth/register", json={
        "name": "Token Test",
        "email": "tokentest@example.com",
        "department": "QA",
        "joining_date": "2025-01-01",
        "password": "secret123"
    })

    assert response.status_code == 201
    emp_id = response.json()['id']

    # Login to get token
    response = client.post("/auth/token", data={
        "username": "tokentest@example.com",
        "password": "secret123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Try to access a protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/employees/{emp_id}", headers=headers)

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid Token"
