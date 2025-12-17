import pytest
from datetime import date
from backend.app.services.scheduler import SchedulerService
from backend.app.services.models import (
    Project, Task, Person, Skill, PersonSkill, TaskRequiredRange
)

def test_load_balancing_distribution():
    scheduler = SchedulerService()
    
    # Common Skill
    skill_py = Skill(id="s1", name="Python")
    
    # 3 People with same skill & efficiency
    people = []
    for i in range(1, 4):
        people.append(Person(
            id=f"p{i}",
            name=f"Person {i}",
            joining_date=date(2023, 1, 1),
            termination_date=None,
            skills=[PersonSkill(id="s1", name="Python", efficiency=1)],
            schedule=[]
        ))

    # 3 Tasks, non-overlapping so 1 person *could* do all
    # Each is 5 days long
    ranges = [
        (date(2023, 6, 1), date(2023, 6, 5)),   # 5 days
        (date(2023, 6, 10), date(2023, 6, 14)), # 5 days
        (date(2023, 6, 20), date(2023, 6, 24))  # 5 days
    ]
    
    tasks = []
    for idx, (start, end) in enumerate(ranges):
        tasks.append(Task(
            id=f"t{idx+1}",
            name=f"Task {idx+1}",
            project_id="proj1",
            skill_id="s1",
            workforce_count=1,
            required_skill=skill_py,
            required_ranges=[TaskRequiredRange(start_date=start, end_date=end)],
            assignees=[]
        ))
        
    project = Project(id="proj1", name="Project Balancing", tasks=tasks)
    
    feasible, infeasible = scheduler.schedule_all([project], people)
    
    # Basic success check
    assert len(feasible) == 1
    assert feasible[0].feasible is True
    
    # Check assignments
    # We expect 3 distinct people to be assigned to the 3 tasks
    # because of the quadratic penalty on workload.
    
    assignments = set()
    assigned_map = {}
    for t in feasible[0].tasks:
        assert len(t.assignees) == 1, f"Task {t.name} should have 1 assignee"
        pid = t.assignees[0].id
        assignments.add(pid)
        assigned_map[t.id] = pid
        
    print(f"Assignments: {assigned_map}")
    
    # Verify that we used 3 different people
    assert len(assignments) == 3, f"Expected 3 unique assignees to distribute load, got {len(assignments)}: {assignments}"
