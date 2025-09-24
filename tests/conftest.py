import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date

from app.main import app as fastapi_app
from app.database import Base, get_db
from sqlalchemy.pool import StaticPool
from app import crud,models

# SQLALCHEMY_DATABASE_URL = "sqlite:///file::memory:?cache=shared"

# engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False, "uri": True})

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,   # 👈 all sessions use same connection
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

fastapi_app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(fastapi_app)


@pytest.fixture
def seed_manager():
    db = TestingSessionLocal()
    existing = crud.get_employee_by_email(db, "manager@example.com")
    if existing:
        db.close()
        return existing
    
    manager = crud.create_employee(
        db,
        name="Manager One",
        email="manager@example.com",
        department="Admin",
        joining_date=date.today(),
        password="managerpass",
        role=models.Role.manager,
    )

    db.close()
    return manager

def register_employee(client, name, email, password, department="IT"):
    response = client.post("/auth/register", json={
        "name": name,
        "email": email,
        "department": department,
        "joining_date": str(date.today()),
        "password": password
    })
    assert response.status_code == 201
    return response.json()

def get_token(client, email, password):
    response = client.post("/auth/token", data={
        "username": email,
        "password": password
    })
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(client, email, password):
    token = get_token(client, email, password)
    return {"Authorization": f"Bearer {token}"}