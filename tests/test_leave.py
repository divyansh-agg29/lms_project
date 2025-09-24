import pytest
from datetime import date

# --- Helpers ---

def register_and_login_employee(client, name="Alice", email="alice@example.com", password="pass123"):
    emp = client.post("/auth/register", json={
        "name": name,
        "email": email,
        "department": "Engineering",
        "joining_date": "2024-08-10",
        "password": password
    }).json()
    token = client.post("/auth/token", data={
        "username": email, "password": password
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return emp, headers

def manager_headers(client, seed_manager):
    token = client.post("/auth/token", data={
        "username": "manager@example.com",
        "password": "managerpass"
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- APPLY LEAVE ---

def test_employee_can_apply_leave(client):
    emp, headers = register_and_login_employee(client)
    response = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-01",
        "end_date": "2025-02-05"
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "applied"
    assert data["employee_id"] == emp["id"]


def test_employee_cannot_apply_for_others(client):
    emp1, headers1 = register_and_login_employee(client, "E1", "e1@example.com", "p1")
    emp2, _ = register_and_login_employee(client, "E2", "e2@example.com", "p2")

    response = client.post("/leave/apply", json={
        "employee_id": emp2["id"],   # tries applying for someone else
        "start_date": "2025-02-01",
        "end_date": "2025-02-05"
    }, headers=headers1)
    assert response.status_code == 403


# --- LIST LEAVES ---

def test_list_leaves_self(client):
    emp, headers = register_and_login_employee(client)
    client.post("/leave/apply", json={
        "employee_id": emp["id"], "start_date": "2025-02-01", "end_date": "2025-02-05"
    }, headers=headers)
    resp = client.get(f"/leave/employee/{emp['id']}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["employee_id"] == emp["id"]


def test_manager_can_list_anyone_leaves(client, seed_manager):
    emp, emp_headers = register_and_login_employee(client)
    client.post("/leave/apply", json={
        "employee_id": emp["id"], "start_date": "2025-02-01", "end_date": "2025-02-05"
    }, headers=emp_headers)

    headers = manager_headers(client, seed_manager)
    resp = client.get(f"/leave/employee/{emp['id']}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_manager_cannot_list_leaves_of_nonexistent_employee(client, seed_manager):
    headers = manager_headers(client, seed_manager)
    resp = client.get("/leave/employee/999", headers=headers)
    assert resp.status_code == 404


def test_employee_cannot_view_others_leaves(client):
    emp1, headers1 = register_and_login_employee(client, "E1", "e1@example.com", "p1")
    emp2, headers2 = register_and_login_employee(client, "E2", "e2@example.com", "p2")

    # e1 tries to view e2’s leaves
    resp = client.get(f"/leave/employee/{emp2['id']}", headers=headers1)
    assert resp.status_code == 403


# --- APPROVE ---

def test_manager_can_approve_leave(client, seed_manager):
    emp, headers = register_and_login_employee(client)
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"], "start_date": "2025-02-01", "end_date": "2025-02-05"
    }, headers=headers).json()

    headers_mgr = manager_headers(client, seed_manager)
    resp = client.put(f"/leave/{leave['id']}/approve", headers=headers_mgr)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_manager_cannot_approve_nonexistent_leave(client, seed_manager):
    headers_mgr = manager_headers(client, seed_manager)
    resp = client.put("/leave/999/approve", headers=headers_mgr)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Leave request not found"


def test_employee_cannot_approve_leave(client):
    emp, headers = register_and_login_employee(client)
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"], "start_date": "2025-02-01", "end_date": "2025-02-05"
    }, headers=headers).json()

    resp = client.put(f"/leave/{leave['id']}/approve", headers=headers)
    assert resp.status_code == 403


def test_cannot_approve_already_approved_leave(client, seed_manager):
    emp, headers = register_and_login_employee(client)
    # create leave
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"], "start_date": "2025-02-01", "end_date": "2025-02-05"
    }, headers=headers).json()

    headers_mgr = manager_headers(client, seed_manager)
    # approve the leave
    client.put(f"/leave/{leave['id']}/approve", headers=headers_mgr)

    #again try to approve
    resp = client.put(f"/leave/{leave['id']}/approve", headers=headers_mgr)
    assert resp.status_code == 400
    assert resp.json()['detail'] == "Cannot approve an already approved leave"


def test_cannot_approve_already_rejected_leave(client, seed_manager):
    emp, headers = register_and_login_employee(client)
    # create leave
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"], "start_date": "2025-02-01", "end_date": "2025-02-05"
    }, headers=headers).json()

    headers_mgr = manager_headers(client, seed_manager)
    # reject the leave
    client.put(f"/leave/{leave['id']}/reject", headers=headers_mgr)

    # try to approve
    resp = client.put(f"/leave/{leave['id']}/approve", headers=headers_mgr)
    assert resp.status_code == 400
    assert resp.json()['detail'] == "Cannot approve an already rejected leave"

# --- REJECT ---

def test_manager_can_reject_leave(client, seed_manager):
    emp, headers = register_and_login_employee(client)
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"], "start_date": "2025-03-01", "end_date": "2025-03-03"
    }, headers=headers).json()

    headers_mgr = manager_headers(client, seed_manager)
    resp = client.put(f"/leave/{leave['id']}/reject", headers=headers_mgr)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_manager_cannot_reject_nonexistent_leave(client, seed_manager):
    headers_mgr = manager_headers(client, seed_manager)
    resp = client.put("/leave/999/reject", headers=headers_mgr)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Leave request not found"


def test_employee_cannot_reject_leave(client):
    emp, headers = register_and_login_employee(client)
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"], "start_date": "2025-03-01", "end_date": "2025-03-03"
    }, headers=headers).json()

    resp = client.put(f"/leave/{leave['id']}/reject", headers=headers)
    assert resp.status_code == 403


def test_cannot_reject_already_rejected_leave(client, seed_manager):
    emp, headers = register_and_login_employee(client)
    # create leave
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"], "start_date": "2025-02-01", "end_date": "2025-02-05"
    }, headers=headers).json()

    headers_mgr = manager_headers(client, seed_manager)
    # reject the leave
    client.put(f"/leave/{leave['id']}/reject", headers=headers_mgr)

    # again try to reject
    resp = client.put(f"/leave/{leave['id']}/reject", headers=headers_mgr)
    assert resp.status_code == 400
    assert resp.json()['detail'] == "Cannot reject an already rejected leave"


def test_cannot_reject_already_approved_leave(client, seed_manager):
    emp, headers = register_and_login_employee(client)
    # create leave
    leave = client.post("/leave/apply", json={
        "employee_id": emp["id"], "start_date": "2025-02-01", "end_date": "2025-02-05"
    }, headers=headers).json()

    headers_mgr = manager_headers(client, seed_manager)
    # approve the leave
    client.put(f"/leave/{leave['id']}/approve", headers=headers_mgr)

    # try to reject
    resp = client.put(f"/leave/{leave['id']}/reject", headers=headers_mgr)
    assert resp.status_code == 400
    assert resp.json()['detail'] == "Cannot reject an already approved leave"


# --- VALIDATION CASES ---

def test_leave_before_joining_date(client):
    emp, headers = register_and_login_employee(client)

    response = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2024-08-09",
        "end_date": "2024-08-12"
    }, headers=headers)
    
    assert response.status_code == 400
    assert "before joining date" in response.json()["detail"]


def test_end_date_before_start_date(client):
    emp, headers = register_and_login_employee(client)

    response = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-05",
        "end_date": "2025-02-01"
    }, headers=headers)

    assert response.status_code == 400
    assert response.json()['detail'] == "Invalid date range"

def test_leave_more_than_balance(client):
    emp, headers = register_and_login_employee(client)

    response = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-01",
        "end_date": "2025-02-25"
    }, headers=headers)

    assert response.status_code == 400
    assert response.json()['detail'] == "Requested days exceed leave balance"


def test_overlapping_leaves(client):
    emp, headers = register_and_login_employee(client)
    
    # first leave
    client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-01",
        "end_date": "2025-02-05"
    }, headers=headers)

    # second leave
    response = client.post("/leave/apply", json={
        "employee_id": emp["id"],
        "start_date": "2025-02-04",
        "end_date": "2025-02-07"
    }, headers=headers)

    assert response.status_code == 400
    assert response.json()['detail'] == "Overlapping leave request exists"