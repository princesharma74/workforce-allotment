
import logging
from datetime import date, timedelta
from sqlmodel import Session, SQLModel, create_engine, select
from backend.app.models import Project, Person, Task, Skill, PersonSkillLink, PersonBusyRange, TaskRequiredRange
from backend.app.api.v1.routers.scheduler import run_scheduler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_scheduler_locked_tasks():
    # Setup in-memory DB
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # 1. Create Data
        skill_python = Skill(id="s1", name="Python")
        session.add(skill_python)
        
        # Person 1: Alice (Python expert)
        alice = Person(id="p1", name="Alice", joining_date=date(2023, 1, 1))
        session.add(alice)
        session.add(PersonSkillLink(person_id="p1", skill_id="s1", efficiency=1))
        
        # Person 2: Bob (Python expert)
        bob = Person(id="p2", name="Bob", joining_date=date(2023, 1, 1))
        session.add(bob)
        session.add(PersonSkillLink(person_id="p2", skill_id="s1", efficiency=1))
        
        # Project A
        proj_a = Project(id="prj1", name="Project A")
        session.add(proj_a)
        
        # Task 1: Week 1 (Assigned to Alice) - Locked
        task1 = Task(
            id="t1", name="Task 1", project_id="prj1", skill_id="s1", workforce_count=1,
            required_skill=skill_python
        )
        task1.assignees = [alice] # Lock Task 1 to Alice
        alice.assigned_tasks = [task1] # Bi-directional
        session.add(task1)
        session.add(TaskRequiredRange(task_id="t1", start_date=date(2023, 6, 1), end_date=date(2023, 6, 7)))
        
        # Task 2: Week 1 (Unassigned) - Conflict with Task 1 for Alice
        task2 = Task(
            id="t2", name="Task 2", project_id="prj1", skill_id="s1", workforce_count=1,
            required_skill=skill_python
        )
        session.add(task2)
        session.add(TaskRequiredRange(task_id="t2", start_date=date(2023, 6, 1), end_date=date(2023, 6, 7)))
        
        session.commit()
        
        # 2. Run Scheduler (Dry Run)
        logger.info("Running scheduler...")
        result = run_scheduler(dry_run=True, session=session)
        
        # 3. Analyze Results
        feasible = result["feasible"]
        infeasible = result["infeasible"]
        
        logger.info(f"Feasible Projects: {len(feasible)}")
        logger.info(f"Infeasible Projects: {len(infeasible)}")
        
        assert len(feasible) == 1, "Project A should be feasible"
        proj_res = feasible[0]
        
        # Check Task 1 (Locked)
        t1_res = next((t for t in proj_res.tasks if t.id == "t1"), None)
        assert t1_res is not None
        assert len(t1_res.assignees) == 1
        assert t1_res.assignees[0].id == "p1", "Task 1 should remain assigned to Alice"
        logger.info("Task 1 correctly locked to Alice.")
        
        # Check Task 2 (Unassigned)
        t2_res = next((t for t in proj_res.tasks if t.id == "t2"), None)
        assert t2_res is not None
        assert len(t2_res.assignees) == 1
        assignee_id = t2_res.assignees[0].id
        
        logger.info(f"Task 2 assigned to: {assignee_id}")
        assert assignee_id == "p2", "Task 2 should be assigned to Bob because Alice is busy"
        
        logger.info("Test Passed!")

if __name__ == "__main__":
    test_scheduler_locked_tasks()
