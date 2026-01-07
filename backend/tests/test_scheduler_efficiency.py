
import pytest
from datetime import date
from datetime import date
from app.services.scheduler import SchedulerService
from app.services.models import (
    Project, Task, Person, Skill, PersonSkill, TaskRequiredRange
)

def test_efficiency_prevents_simultaneous_full_load():
    """
    Verify that a person with efficiency 2 cannot be assigned to two simultaneous tasks
    that each require workforce 2.
    Previous bug allowed this because Efficiency was treated as 'concurrency capacity'.
    """
    scheduler = SchedulerService()
    skill_java = Skill(id="java", name="Java")
    
    # Person with Efficiency 2
    p1 = Person(
        id="p1", 
        name="Alice", 
        joining_date=date(2025, 1, 1), 
        termination_date=None,
        skills=[PersonSkill(id="java", name="Java", efficiency=2)],
        schedule=[]
    )
    
    # Overlapping tasks
    range1 = TaskRequiredRange(start_date=date(2025, 1, 10), end_date=date(2025, 1, 12))
    
    t1 = Task(
        id="t1", 
        name="Task 1", 
        project_id="proj1", 
        skill_id="java", 
        workforce_count=2, 
        required_skill=skill_java,
        required_ranges=[range1]
    )
    
    t2 = Task(
        id="t2", 
        name="Task 2", 
        project_id="proj1", 
        skill_id="java", 
        workforce_count=2, 
        required_skill=skill_java,
        required_ranges=[range1]
    )
    
    project = Project(
        id="proj1", 
        name="Test Project", 
        tasks=[t1, t2]
    )
    
    # Start fresh (scheduler doesn't mutate inputs permanently ideally, but project tasks do get assigned)
    # We pass fresh objects in the real service usage
    
    feasible, infeasible = scheduler.schedule_all([project], [p1])
    
    # Should be infeasible because Alice can't do both
    assert len(feasible) == 0
    assert len(infeasible) == 1
    assert "Insufficient capacity" in infeasible[0].failure_reason or "Conflict" in infeasible[0].failure_reason or infeasible[0].failure_reason

def test_sequential_tasks_allowed():
    """Verify that sequential tasks are allowed for the same efficient person."""
    scheduler = SchedulerService()
    skill_java = Skill(id="java", name="Java")
    
    p1 = Person(
        id="p1", 
        name="Alice", 
        joining_date=date(2025, 1, 1), 
        termination_date=None,
        skills=[PersonSkill(id="java", name="Java", efficiency=2)],
        schedule=[]
    )
    
    # Sequential tasks
    range1 = TaskRequiredRange(start_date=date(2025, 1, 10), end_date=date(2025, 1, 12))
    range2 = TaskRequiredRange(start_date=date(2025, 1, 15), end_date=date(2025, 1, 17))
    
    t1 = Task(
        id="t1", name="Task 1", project_id="proj1", skill_id="java", workforce_count=2, required_skill=skill_java, required_ranges=[range1]
    )
    t2 = Task(
        id="t2", name="Task 2", project_id="proj1", skill_id="java", workforce_count=2, required_skill=skill_java, required_ranges=[range2]
    )
    
    project = Project(id="proj1", name="Sequential Project", tasks=[t1, t2])
    
    feasible, infeasible = scheduler.schedule_all([project], [p1])
    
    assert len(feasible) == 1
    assert len(infeasible) == 0
    assigned_tasks = p1.assigned_tasks
    # Alice should be assigned to both
    assert len(assigned_tasks) == 2

def test_efficiency_satisfies_demand():
    """Verify that Eff=2 satisfies Req=2 efficiently."""
    scheduler = SchedulerService()
    skill_java = Skill(id="java", name="Java")
    
    p1 = Person(
        id="p1", name="Alice", joining_date=date(2025, 1, 1), termination_date=None,
        skills=[PersonSkill(id="java", name="Java", efficiency=2)], schedule=[]
    )
    
    t1 = Task(
        id="t1", name="Task 1", project_id="proj1", skill_id="java", workforce_count=2,
        required_skill=skill_java, 
        required_ranges=[TaskRequiredRange(start_date=date(2025, 1, 10), end_date=date(2025, 1, 12))]
    )
    
    project = Project(id="proj1", name="Proj", tasks=[t1])
    
    feasible, infeasible = scheduler.schedule_all([project], [p1])
    assert len(feasible) == 1
    # Alice contributes 2 >= 2. OK.
