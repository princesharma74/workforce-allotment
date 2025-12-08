
from sqlmodel import SQLModel, Session, create_engine, select
from datetime import date
from typing import List

# Import app models and scheduler
# We assume the script is run from the project root.
from backend.app.models import Project, Person, Task, Skill, TaskRequiredRange, PersonBusyRange
from backend.app.services.scheduler import SchedulerService

def test_scheduler_workforce_count():
    # Setup in-memory DB
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Create Data
        skill_python = Skill(name="Python")
        session.add(skill_python)
        
        # Person 1: Alice (Available)
        alice = Person(name="Alice", joining_date=date(2024, 1, 1))
        alice.skills = [skill_python]
        session.add(alice)
        
        # Person 2: Bob (Available)
        bob = Person(name="Bob", joining_date=date(2024, 1, 1))
        bob.skills = [skill_python]
        session.add(bob)
        
        # Project
        project = Project(name="Test Project")
        session.add(project)
        session.commit()
        session.refresh(project)
        session.refresh(alice)
        session.refresh(bob)
        session.refresh(skill_python)

        # Task: Needs 2 Python devs for 5 days
        task = Task(
            name="Backend Dev",
            project_id=project.id,
            skill_id=skill_python.id,
            workforce_count=2
        )
        task.required_ranges = [
            TaskRequiredRange(start_date=date(2024, 1, 1), end_date=date(2024, 1, 5))
        ]
        session.add(task)
        session.commit()
        
        # Run Scheduler
        scheduler = SchedulerService(session)
        print("Running scheduler...")
        feasible, infeasible = scheduler.schedule_all(commit=True)
        
        # Check Results
        print(f"Feasible Projects: {len(feasible)}")
        print(f"Infeasible Projects: {len(infeasible)}")
        
        if len(feasible) != 1:
            print("FAILURE: Project should be feasible.")
            if infeasible:
                print(f"Failure Reason: {infeasible[0].failure_reason}")
                for t in infeasible[0].tasks:
                    print(f"Task {t.name} (needed {t.workforce_count}): {t.failure_reason}, assigned: {len(t.assignees)}")
            else:
                print("No results returned?")
            return

        project_result = feasible[0]
        task_result = project_result.tasks[0]
        
        print(f"Task assigned to: {[p.name for p in task_result.assignees]}")
        
        if len(task_result.assignees) != 2:
            print(f"FAILURE: Expected 2 assignees, got {len(task_result.assignees)}")
        else:
            print("SUCCESS: Task assigned to 2 people correctly.")

if __name__ == "__main__":
    test_scheduler_workforce_count()
