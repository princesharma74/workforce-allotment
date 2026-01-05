import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from backend.app.main import app
from backend.app.database import get_session
from backend.app.models import Person, Skill, PersonSkillLink
from backend.app.schemas import PersonCreate, PersonSkillCreate

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_create_person_with_preference(client: TestClient):
    response = client.post(
        "/api/v1/people/",
        json={
            "name": "Pref User",
            "joining_date": "2023-01-01",
            "skills": [
                {"name": "Python", "efficiency": 2, "preference_score": 5}
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Pref User"
    assert len(data["skills"]) == 1
    assert data["skills"][0]["name"] == "Python"
    assert data["skills"][0]["efficiency"] == 2
    assert data["skills"][0]["preference_score"] == 5

    # Verify persistence via GET
    response = client.get("/api/v1/people/")
    assert response.status_code == 200
    data = response.json()
    person = next(p for p in data if p["name"] == "Pref User")
    assert person["skills"][0]["preference_score"] == 5

def test_create_person_without_preference_backward_compatibility(client: TestClient):
    response = client.post(
        "/api/v1/people/",
        json={
            "name": "Legacy User",
            "joining_date": "2023-01-01",
            "skills": [
                {"name": "Java", "efficiency": 3}
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Legacy User"
    assert len(data["skills"]) == 1
    assert data["skills"][0]["name"] == "Java"
    assert data["skills"][0]["efficiency"] == 3
    # Check default value
    assert data["skills"][0]["preference_score"] == 1

    # Verify persistence via GET
    response = client.get("/api/v1/people/")
    assert response.status_code == 200
    data = response.json()
    person = next(p for p in data if p["name"] == "Legacy User")
    assert person["skills"][0]["preference_score"] == 1

def test_update_person_preference(client: TestClient):
    # 1. Create person
    response = client.post(
        "/api/v1/people/",
        json={
            "name": "Update User",
            "joining_date": "2023-01-01",
            "skills": [
                {"name": "Go", "efficiency": 1, "preference_score": 1}
            ]
        }
    )
    person_id = response.json()["id"]

    # 2. Update preference
    response = client.put(
        f"/api/v1/people/{person_id}",
        json={
            "skills": [
                {"name": "Go", "efficiency": 1, "preference_score": 10}
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["skills"][0]["preference_score"] == 10

    # 3. Verify persistence
    response = client.get(f"/api/v1/people/")
    data = response.json()
    person = next(p for p in data if p["id"] == person_id)
    assert person["skills"][0]["preference_score"] == 10
