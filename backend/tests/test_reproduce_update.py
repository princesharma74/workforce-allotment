
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
from datetime import date

from backend.app.main import app
from backend.app.database import get_session
from backend.app.models import Person, Skill

# Setup in-memory database for testing
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
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

def test_reproduce_update_error(client: TestClient):
    # 1. Create Person
    resp = client.post("/api/v1/people/", json={
        "name": "TestUser",
        "joining_date": "2023-01-01",
        "skills": [{"name": "Python", "efficiency": 1}]
    })
    assert resp.status_code == 200
    person_id = resp.json()["id"]

    # 2. Update Person - Same Skills, different efficiency
    resp = client.put(f"/api/v1/people/{person_id}", json={
        "name": "TestUserUpdated",
        "skills": [{"name": "Python", "efficiency": 2}]
    })
    if resp.status_code != 200:
        print(resp.text)
    assert resp.status_code == 200
    assert resp.json()["skills"][0]["efficiency"] == 2

    # 3. Update Person - Add new skill
    resp = client.put(f"/api/v1/people/{person_id}", json={
        "name": "TestUserUpdated",
        "skills": [{"name": "Python", "efficiency": 2}, {"name": "Go", "efficiency": 1}]
    })
    if resp.status_code != 200:
        print(resp.text)
    assert resp.status_code == 200
    assert len(resp.json()["skills"]) == 2

    # 4. Update Person - Empty skills
    resp = client.put(f"/api/v1/people/{person_id}", json={
        "skills": []
    })
    assert resp.status_code == 200
    assert len(resp.json()["skills"]) == 0
