def test_create_employee(client):
    response = client.post("/employees", json={
        "name": "Alice",
        "email": "alice@example.com",
        "department": "Engineering",
        "joining_date": "2025-01-01"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert "id" in data


def test_get_employee(client):
    # Create employee first
    client.post("/employees", json={
        "name": "Bob",
        "email": "bob@example.com",
        "department": "HR",
        "joining_date": "2025-01-01"
    })

    # Fetch employee
    response = client.get("/employees/1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Bob"
    assert data["email"] == "bob@example.com"


def test_duplicate_email(client):
    # Create first employee
    client.post("/employees", json={
        "name": "Carol",
        "email": "carol@example.com",
        "department": "Finance",
        "joining_date": "2025-01-01"
    })

    # Try creating with same email
    response = client.post("/employees", json={
        "name": "Carol2",
        "email": "carol@example.com",
        "department": "Finance",
        "joining_date": "2025-01-02"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already exist"


def test_get_balance(client):
    # Create employee
    emp = client.post("/employees", json={
        "name": "David",
        "email": "david@example.com",
        "department": "IT",
        "joining_date": "2025-01-01"
    }).json()

    response = client.get(f"/employees/{emp['id']}/balance")
    assert response.status_code == 200
    data = response.json()
    assert data["employee_id"] == emp["id"]
    assert "leave_balance" in data



def test_get_nonexistent_employee(client):
    response = client.get("/employees/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found"


def test_balance_nonexistent_employee(client):
    response = client.get("/employees/999/balance")
    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found"


def test_create_employee_missing_name(client):
    response = client.post("/employees", json={
        "email": "noname@example.com",
        "department": "HR",
        "joining_date": "2025-01-01"
    })
    # Pydantic validation error
    assert response.status_code == 422


def test_create_employee_missing_email(client):
    response = client.post("/employees", json={
        "name": "NoEmail",
        "department": "Finance",
        "joining_date": "2025-01-01"
    })
    assert response.status_code == 422


def test_create_employee_invalid_email(client):
    response = client.post("/employees", json={
        "name": "Invalid",
        "email": "not-an-email",
        "department": "Sales",
        "joining_date": "2025-01-01"
    })
    assert response.status_code == 422  # invalid email format


def test_list_employees_with_limit(client):
    # Create 3 employees
    for i in range(3):
        client.post("/employees", json={
            "name": f"Emp{i}",
            "email": f"emp{i}@example.com",
            "department": "Dept",
            "joining_date": "2025-01-01"
        })

    # Fetch only 2
    response = client.get("/employees?skip=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_employees_with_skip(client):
    # Create employees
    for i in range(3):
        client.post("/employees", json={
            "name": f"Emp{i}",
            "email": f"emp{i}@example.com",
            "department": "Dept",
            "joining_date": "2025-01-01"
        })

    response = client.get("/employees?skip=2&limit=10")
    assert response.status_code == 200
    data = response.json()
    # Only 1 left after skipping first 2
    assert len(data) == 1
