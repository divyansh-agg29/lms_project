## CREATE EMPLOYEE
def test_manager_can_create_employee(client, seed_manager):
    # get token from seeded manager
    token = client.post("/auth/token",data={
        "username": "manager@example.com",
        "password": "managerpass"
    }).json()['access_token']
    headers={"Authorization":f"Bearer {token}"}

    response = client.post("/employees",json={
        "name": "Alice",
        "email": "alice@example.com",
        "department": "Engineering",
        "joining_date": "2025-01-01",
        "password": "password123",
        "role": "employee"
    }, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["role"] == "employee"


def test_employee_cannot_create_employee(client):
    # Register an employee
    client.post("/auth/register", json={
        "name": "Bob",
        "email": "bob@example.com",
        "department": "HR",
        "joining_date": "2025-01-01",
        "password": "password123"
    })

    # Login as Bob
    token = client.post("/auth/token", data={
        "username": "bob@example.com", "password": "password123"
    }).json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # Try to create another employee
    response = client.post("/employees", json={
        "name": "Charlie",
        "email": "charlie@example.com",
        "department": "Finance",
        "joining_date": "2025-01-01",
        "password": "secret123",
        "role": "employee"
    }, headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have permission for this action"


def test_duplicate_email(client, seed_manager):
    token = client.post('/auth/token', data={
        'username': 'manager@example.com', 'password': 'managerpass'
    }).json()['access_token']

    headers = {"Authorization": f"Bearer {token}"}

    client.post("/employees", json={
        "name": "Carol",
        "email": "carol@example.com",
        "department": "Finance",
        "joining_date": "2025-01-01",
        "password": "password123",
        "role": "employee"
    }, headers=headers)

    response = client.post("/employees", json={
        "name": "Carol2",
        "email": "carol@example.com",
        "department": "Finance",
        "joining_date": "2025-01-02",
        "password": "password456",
        "role": "employee"
    }, headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already exist"


## GET EMPLOYEE
def test_employee_can_fetch_self(client):
    emp = client.post("/auth/register", json={
        "name": "David",
        "email": "david@example.com",
        "department": "IT",
        "joining_date": "2025-01-01",
        "password": "mypassword"
    }).json()

    token = client.post("/auth/token", data={
        "username": "david@example.com", "password": "mypassword"
    }).json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/employees/{emp['id']}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["email"] == "david@example.com"


def test_employee_cannot_fetch_others(client):
    # Register two employees
    emp1 = client.post("/auth/register", json={
        "name": "E1", "email": "e1@example.com", "department": "IT", "joining_date": "2025-01-01", "password": "p1"
    }).json()
    emp2 = client.post("/auth/register", json={
        "name": "E2", "email": "e2@example.com", "department": "HR", "joining_date": "2025-01-01", "password": "p2"
    }).json()

    token = client.post("/auth/token", data={"username": "e1@example.com", "password": "p1"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # e1 tries to fetch e2
    resp = client.get(f"/employees/{emp2['id']}", headers=headers)
    assert resp.status_code == 403


def test_manager_can_fetch_any_employee(client, seed_manager):
    # Manager login
    token = client.post("/auth/token", data={
        "username": "manager@example.com", "password": "managerpass"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Register employee
    emp = client.post("/auth/register", json={
        "name": "Frank", "email": "frank@example.com", "department": "Finance", "joining_date": "2025-01-01", "password": "pass"
    }).json()

    resp = client.get(f"/employees/{emp['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "frank@example.com"


def test_manager_cannot_fetch_nonexistent_employee(client,seed_manager):
    # Manager login
    token = client.post("/auth/token", data={
        "username": "manager@example.com", "password": "managerpass"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/employees/999", headers=headers)
    assert resp.status_code == 404
    assert resp.json()['detail'] == "Employee not found"


## GET BALANCE
def test_get_balance_self(client):
    emp = client.post("/auth/register", json={
        "name": "Grace",
        "email": "grace@example.com",
        "department": "Finance",
        "joining_date": "2025-01-01",
        "password": "pass"
    }).json()

    token = client.post("/auth/token", data={
        "username": "grace@example.com", "password": "pass"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/employees/{emp['id']}/balance", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["employee_id"] == emp["id"]


def test_employee_cannot_fetch_others_balance(client):
    # Register two employees
    emp1 = client.post("/auth/register", json={
        "name": "E1", "email": "e1@example.com", "department": "IT", "joining_date": "2025-01-01", "password": "p1"
    }).json()
    emp2 = client.post("/auth/register", json={
        "name": "E2", "email": "e2@example.com", "department": "HR", "joining_date": "2025-01-01", "password": "p2"
    }).json()

    token = client.post("/auth/token", data={"username": "e1@example.com", "password": "p1"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/employees/{emp2['id']}/balance", headers=headers)
    assert response.status_code == 403
    assert response.json()['detail'] == "You can only view your own balance"


def test_manager_can_view_balance_of_anyone(client, seed_manager):
    token = client.post("/auth/token", data={
        "username": "manager@example.com", "password": "managerpass"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    emp = client.post("/auth/register", json={
        "name": "Hank", "email": "hank@example.com", "department": "IT", "joining_date": "2025-01-01", "password": "pass"
    }).json()

    resp = client.get(f"/employees/{emp['id']}/balance", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["employee_id"] == emp["id"]


def test_manager_cannot_view_balance_of_nonexistent_employee(client, seed_manager):
    token = client.post("/auth/token", data={
        "username": "manager@example.com", "password": "managerpass"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}


    resp = client.get("/employees/999/balance", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Employee not found"


## LIST EMPLOYEE
def test_list_employees_manager_only(client, seed_manager):
    token = client.post("/auth/token", data={
        "username": "manager@example.com", "password": "managerpass"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create employees
    for i in range(3):
        client.post("/auth/register", json={
            "name": f"Emp{i}", "email": f"emp{i}@example.com", "department": "Dept", "joining_date": "2025-01-01", "password": "p"
        })

    resp = client.get("/employees?skip=0&limit=2", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_employee_cannot_list_employees(client):
    client.post("/auth/register", json={
        "name": "Ivy", "email": "ivy@example.com", "department": "QA", "joining_date": "2025-01-01", "password": "p"
    })

    token = client.post("/auth/token", data={
        "username": "ivy@example.com", "password": "p"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/employees", headers=headers)
    assert resp.status_code == 403

