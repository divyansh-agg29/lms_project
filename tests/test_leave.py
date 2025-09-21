def create_employee(client):
    return client.post("/employees", json={
        "name": "Alice",
        "email": "alice@example.com",
        "department": "Engineering",
        "joining_date": "2025-01-01"
    }).json()


def test_apply_leave(client):
    emp = create_employee(client)
    response = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-01",
        "end_date": "2025-02-05"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "applied"
    assert data["num_days"] == 5


def test_list_leaves_for_employee(client):
    emp = create_employee(client)

    # Apply leave
    client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-01",
        "end_date": "2025-02-05"
    })

    response = client.get(f"/leave/employee/{emp['id']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["employee_id"] == emp["id"]


def test_approve_leave(client):
    emp = create_employee(client)
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-01",
        "end_date": "2025-02-05"
    }).json()

    response = client.put(f"/leave/{leave['id']}/approve")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["employee_id"] == emp["id"]


def test_reject_leave(client):
    emp = create_employee(client)
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-03-01",
        "end_date": "2025-03-03"
    }).json()

    response = client.put(f"/leave/{leave['id']}/reject")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"

def test_leave_nonexistent_employee(client):
    response = client.post("/leave/apply", json={
        "employee_id": 1,
        "start_date": "2025-02-25",
        "end_date": "2025-02-28"
    })
    assert response.status_code == 404
    assert "Employee not found" in response.json()["detail"]


def test_leave_before_joining_date(client):
    emp = client.post("/employees", json={
        "name": "Eve",
        "email": "eve@example.com",
        "department": "Sales",
        "joining_date": "2025-03-01"
    }).json()

    response = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-25",
        "end_date": "2025-02-28"
    })
    assert response.status_code == 400
    assert "before joining date" in response.json()["detail"]


def test_invalid_date_range(client):
    emp = create_employee(client)
    response = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-10",
        "end_date": "2025-02-05"
    })
    assert response.status_code == 400
    assert "Invalid date range" in response.json()["detail"]


def test_overlapping_leave(client):
    emp = create_employee(client)
    client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-01",
        "end_date": "2025-02-05"
    })

    response = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-03",
        "end_date": "2025-02-06"
    })
    assert response.status_code == 400
    assert "Overlapping" in response.json()["detail"]


def test_insufficient_leave_balance(client):
    emp = create_employee(client)
    response = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-03-01",
        "end_date": "2025-03-30"   # 30 days > default balance
    })
    assert response.status_code == 400
    assert "exceed leave balance" in response.json()["detail"]

def test_approve_nonexistent_leave(client):
    response = client.put("/leave/999/approve")
    assert response.status_code == 404
    assert response.json()["detail"] == "Leave request not found"


def test_reject_nonexistent_leave(client):
    response = client.put("/leave/999/reject")
    assert response.status_code == 404
    assert response.json()["detail"] == "Leave request not found"


def test_double_approve(client):
    emp = create_employee(client)
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-01",
        "end_date": "2025-02-05"
    }).json()

    client.put(f"/leave/{leave['id']}/approve")
    response = client.put(f"/leave/{leave['id']}/approve")
    assert response.status_code == 400
    assert "Only 'applied' leaves" in response.json()["detail"]


def test_double_reject(client):
    emp = create_employee(client)
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-03-01",
        "end_date": "2025-03-03"
    }).json()

    client.put(f"/leave/{leave['id']}/reject")
    response = client.put(f"/leave/{leave['id']}/reject")
    assert response.status_code == 400
    assert "already rejected" in response.json()["detail"]


def test_reject_approved_leave(client):
    emp = create_employee(client)
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-04-01",
        "end_date": "2025-04-02"
    }).json()

    client.put(f"/leave/{leave['id']}/approve")
    response = client.put(f"/leave/{leave['id']}/reject")
    assert response.status_code == 400
    assert "already approved" in response.json()["detail"]


def test_list_leaves_for_nonexistent_employee(client):
    response = client.get(f"/leave/employee/1")
    assert response.status_code == 404
    data = response.json()
    assert "Employee not found" in response.json()["detail"]