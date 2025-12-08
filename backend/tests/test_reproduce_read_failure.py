
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

def test_reproduce_read_people(client: TestClient):
    # 1. Create Person
    resp = client.post("/api/v1/people/", json={
        "name": "TestReadUser",
        "joining_date": "2023-01-01",
        "skills": [{"name": "Java", "efficiency": 3}]
    })
    assert resp.status_code == 200
    
    # 2. Read People
    resp = client.get("/api/v1/people/")
    assert resp.status_code == 200
    people = resp.json()
    assert len(people) == 1
    p = people[0]
    assert p["name"] == "TestReadUser"
    assert len(p["skills"]) == 1
    assert p["skills"][0]["name"] == "Java"
    assert p["skills"][0]["efficiency"] == 3
