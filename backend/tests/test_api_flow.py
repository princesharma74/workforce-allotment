
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
from datetime import date

from backend.app.main import app
from backend.app.database import get_session
from backend.app.models import Person, Skill, Project, Task, PersonSkillLink

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

def test_skills_crud(client: TestClient):
    # Create
    response = client.post("/api/v1/skills/", json={"name": "Rust"})
    assert response.status_code == 200
    assert response.json()["name"] == "Rust"
    
    # Duplicate create (should return existing)
    response = client.post("/api/v1/skills/", json={"name": "Rust"})
    assert response.status_code == 200
    
    # Read
    response = client.get("/api/v1/skills/")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_create_and_read_person(client: TestClient):
    # Test creating a person with skills and busy ranges
    person_data = {
        "name": "Alice",
        "email": "alice@example.com",
        "joining_date": "2023-01-01",
        "skills": [{"name": "Python", "efficiency": 1}, {"name": "SQL", "efficiency": 1}],
        "busy_ranges": [
            {"start": "2023-02-01", "end": "2023-02-10"}
        ]
    }
    response = client.post("/api/v1/people/", json=person_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"
    assert len(data["skills"]) == 2
    assert len(data["busy_ranges"]) == 1
    assert data["busy_ranges"][0]["start"] == "2023-02-01"

    # Test reading people
    response = client.get("/api/v1/people/")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_create_and_read_project(client: TestClient):
    # Create Project
    project_data = {
        "name": "Project Alpha",
        "tapeout_date": "2023-12-01",
        "compilers_count": 5,
        "instances_per_compiler": 2,
        "duration_weeks": 4,
        "design_type": "Hierarchical",
        "package_type": "Flipchip",
        "status": "Draft",
        "tasks": [
            {
                "name": "Backend Dev",
                "skill_name": "Python",
                "required_ranges": [
                    {"start": "2023-03-01", "end": "2023-03-15"}
                ]
            }
        ]
    }
    response = client.post("/api/v1/projects/", json=project_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Project Alpha"
    assert data["tapeout_date"] == "2023-12-01"
    assert data["status"] == "Draft"
    assert data["design_type"] == "Hierarchical"
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["name"] == "Backend Dev"
    task_id = data["tasks"][0]["id"]

    # Read Projects
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    assert len(response.json()) == 1

def test_manual_assignment(client: TestClient, session: Session):
    # Setup Data
    # 1. Person
    client.post("/api/v1/people/", json={
        "name": "Bob",
        "joining_date": "2023-01-01"
    })
    person = session.exec(select(Person).where(Person.name == "Bob")).first()
    
    # 2. Project & Task
    client.post("/api/v1/projects/", json={
        "name": "Test Project",
        "tasks": [
            {"name": "Task 1", "skill_name": "Go", "required_ranges": []}
        ]
    })
    task = session.exec(select(Task)).first()
    
    # Assign
    response = client.put(f"/api/v1/projects/tasks/{task.id}/assign?person_id={person.id}")
    assert response.status_code == 200
    assert response.json()["task"] == "Task 1"
    assert response.json()["person"] == "Bob"
    
    # Verify assignment persistence
    session.refresh(task)
    assert len(task.assignees) == 1
    assert task.assignees[0].id == person.id

def test_bulk_assignment(client: TestClient, session: Session):
    # Setup Data
    client.post("/api/v1/people/", json={"name": "P1", "joining_date": "2023-01-01"})
    client.post("/api/v1/people/", json={"name": "P2", "joining_date": "2023-01-01"})
    p1 = session.exec(select(Person).where(Person.name == "P1")).first()
    p2 = session.exec(select(Person).where(Person.name == "P2")).first()
    
    client.post("/api/v1/projects/", json={
        "name": "Bulk P",
        "tasks": [
            {"name": "T1", "skill_name": "S1", "required_ranges": []},
            {"name": "T2", "skill_name": "S2", "required_ranges": []}
        ]
    })
    t1 = session.exec(select(Task).where(Task.name == "T1")).first()
    t2 = session.exec(select(Task).where(Task.name == "T2")).first()
    
    # Bulk Assign
    bulk_data = {
        "assignments": [
            {"task_id": t1.id, "person_id": p1.id},
            {"task_id": t2.id, "person_id": p2.id}
        ]
    }
    response = client.post("/api/v1/projects/assignments/bulk", json=bulk_data)
    assert response.status_code == 200
    assert response.json()["count"] == 2
    
    # Verify
    session.refresh(t1)
    session.refresh(t2)
    assert t1.assignees[0].id == p1.id
    assert t2.assignees[0].id == p2.id

def test_scheduler_run(client: TestClient, session: Session):
    # Setup Feasible Scenario
    # Person: Charlie, Skill: Java, Available
    client.post("/api/v1/people/", json={
        "name": "Charlie",
        "joining_date": "2023-01-01",
        "skills": [{"name": "Java", "efficiency": 1}],
        "busy_ranges": []
    })
    
    # Project: Task needs Java
    client.post("/api/v1/projects/", json={
        "name": "Java App",
        "tasks": [
            {
                "name": "Core Logic", 
                "skill_name": "Java", 
                "required_ranges": [{"start": "2023-05-01", "end": "2023-05-05"}]
            }
        ]
    })
    
    # Run Scheduler (Dry Run)
    response = client.post("/api/v1/scheduler/run?dry_run=true")
    assert response.status_code == 200
    res = response.json()
    assert len(res["feasible"]) > 0
    # Check assignment in result but NOT in DB
    
    task_res = res["feasible"][0]["tasks"][0]
    assert len(task_res["assignees"]) == 1
    
    task = session.exec(select(Task).where(Task.name == "Core Logic")).first()
    session.refresh(task)
    assert len(task.assignees) == 0 # Dry run shouldn't persist
    
    # Run Scheduler (Commit)
    response = client.post("/api/v1/scheduler/run?dry_run=false")
    assert response.status_code == 200
    
    session.refresh(task)
    assert len(task.assignees) == 1 # Should persist

def test_workforce_count_constraint(client: TestClient, session: Session):
    # Setup: 2 People with Java
    client.post("/api/v1/people/", json={"name": "Dev1", "joining_date": "2023-01-01", "skills": [{"name": "Java", "efficiency": 1}]})
    client.post("/api/v1/people/", json={"name": "Dev2", "joining_date": "2023-01-01", "skills": [{"name": "Java", "efficiency": 1}]})
    
    # Project with task requiring workforce_count=2
    client.post("/api/v1/projects/", json={
        "name": "Big Project",
        "tasks": [
            {
                "name": "Big Task", 
                "skill_name": "Java", 
                "workforce_count": 2,
                "required_ranges": [{"start": "2023-06-01", "end": "2023-06-10"}]
            }
        ]
    })
    
    # Run Scheduler
    response = client.post("/api/v1/scheduler/run")
    assert response.status_code == 200
    res = response.json()
    assert len(res["feasible"]) == 1
    
    # Verify both assigned
    task_res = res["feasible"][0]["tasks"][0]
    assert len(task_res["assignees"]) == 2
    assert task_res["workforce_count"] == 2
    
    # Verify in DB
    task = session.exec(select(Task).where(Task.name == "Big Task")).first()
    assert len(task.assignees) == 2

def test_person_validation_error(client: TestClient):
    response = client.post("/api/v1/people/", json={
        "name": "Bad Date",
        "joining_date": "2023-01-01",
        "busy_ranges": [{"start": "2023-01-01"}] # Missing end
    })
    assert response.status_code == 422

def test_delete_and_update_flow(client: TestClient, session: Session):
    # 1. Skills
    # Create
    response = client.post("/api/v1/skills/", json={"name": "Rust"})
    assert response.status_code == 200
    skill_id = response.json()["id"]
    
    # Update
    response = client.put(f"/api/v1/skills/{skill_id}", json={"name": "RustLang"})
    assert response.status_code == 200
    assert response.json()["name"] == "RustLang"
    
    # Delete
    response = client.delete(f"/api/v1/skills/{skill_id}")
    assert response.status_code == 200
    
    # Verify Delete
    response = client.get("/api/v1/skills/")
    skills = response.json()
    assert not any(s["id"] == skill_id for s in skills)

    # 2. People
    # Create
    response = client.post("/api/v1/people/", json={
        "name": "DeleteMe",
        "joining_date": "2023-01-01"
    })
    person_id = response.json()["id"]
    
    # Update
    response = client.put(f"/api/v1/people/{person_id}", json={
        "name": "UpdatedName",
        "skills": [{"name": "RustLang", "efficiency": 1}] 
    })
    assert response.status_code == 200
    assert response.json()["name"] == "UpdatedName"
    assert len(response.json()["skills"]) == 1
    
    # Delete
    response = client.delete(f"/api/v1/people/{person_id}")
    assert response.status_code == 200
    
    # Verify
    person = session.get(Person, person_id)
    assert person is None
    
    # 3. Projects & Tasks
    # Create
    response = client.post("/api/v1/projects/", json={
        "name": "DeleteProj",
        "tasks": [{"name": "TaskToDel", "skill_name": "Go", "required_ranges": []}]
    })
    proj_data = response.json()
    proj_id = proj_data["id"]
    task_id = proj_data["tasks"][0]["id"]
    
    # Update Project
    response = client.put(f"/api/v1/projects/{proj_id}", json={"name": "ProjUpdated"})
    assert response.status_code == 200
    assert response.json()["name"] == "ProjUpdated"
    
    # Update Task
    response = client.put(f"/api/v1/projects/tasks/{task_id}", json={"name": "TaskUpdated", "skill_name": "C++"})
    assert response.status_code == 200
    assert response.json()["name"] == "TaskUpdated"
    assert response.json()["required_skill"]["name"] == "C++"
    
    # Delete Task
    response = client.delete(f"/api/v1/projects/tasks/{task_id}")
    assert response.status_code == 200
    task = session.get(Task, task_id)
    assert task is None
    
    # Delete Project
    response = client.delete(f"/api/v1/projects/{proj_id}")
    assert response.status_code == 200
    project = session.get(Project, proj_id)
    assert project is None
