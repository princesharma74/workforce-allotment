import pytest
from datetime import date, timedelta
from backend.app.services.scheduler import SchedulerService
from backend.app.services.models import (
    Project, Task, Person, Skill, PersonSkill, TaskRequiredRange, PersonBusyRange
)

def test_scheduler_failure_reasons():
    scheduler = SchedulerService()
    
    # Setup Skills
    skill_java = Skill(id="s1", name="Java")
    
    # Setup Person (Efficiency 1)
    p1 = Person(
        id="p1", 
        name="Alice", 
        joining_date=date(2023, 1, 1), 
        termination_date=None,
        skills=[PersonSkill(id="s1", name="Java", efficiency=1)],
        schedule=[]
    )
    
    # Setup Project & Task
    # Task needs efficiency 2 (but we only have 1 person with eff 1)
    t1_range = TaskRequiredRange(start_date=date(2023, 6, 1), end_date=date(2023, 6, 5))
    t1 = Task(
        id="t1",
        name="Task 1",
        project_id="proj1",
        skill_id="s1",
        workforce_count=2, # Needs 2
        required_skill=skill_java,
        required_ranges=[t1_range],
        assignees=[]
    )
    
    project = Project(id="proj1", name="Proj 1", tasks=[t1])
    
    feasible, infeasible = scheduler.schedule_all([project], [p1])
    
    assert len(infeasible) == 1
    result = infeasible[0]
    assert result.feasible is False
    
    # Check task failure reason
    task_res = result.tasks[0]
    print(f"Failure Reason: {task_res.failure_reason}")
    
    assert "Insufficient workforce" in task_res.failure_reason
    assert "Needed efficiency 2" in task_res.failure_reason
    assert "found 1" in task_res.failure_reason
    
def test_scheduler_busy_reason():
    scheduler = SchedulerService()
    skill_java = Skill(id="s1", name="Java")
    
    # Person busy during task
    busy_range = PersonBusyRange(start_date=date(2023, 6, 1), end_date=date(2023, 6, 5))
    p1 = Person(
        id="p1", 
        name="Bob", 
        joining_date=date(2023, 1, 1), 
        termination_date=None,
        skills=[PersonSkill(id="s1", name="Java", efficiency=1)],
        schedule=[busy_range]
    )
    
    t1_range = TaskRequiredRange(start_date=date(2023, 6, 1), end_date=date(2023, 6, 5))
    t1 = Task(
        id="t1",
        name="Task 1",
        project_id="proj1",
        skill_id="s1",
        workforce_count=1,
        required_skill=skill_java,
        required_ranges=[t1_range],
        assignees=[]
    )
    
    project = Project(id="proj1", name="Proj 1", tasks=[t1])
    
    feasible, infeasible = scheduler.schedule_all([project], [p1])
    
    assert len(infeasible) == 1
    task_res = infeasible[0].tasks[0]
    print(f"Failure Reason: {task_res.failure_reason}")
    
    assert "Rejections" in task_res.failure_reason
    assert "Busy in manual schedule" in task_res.failure_reason
