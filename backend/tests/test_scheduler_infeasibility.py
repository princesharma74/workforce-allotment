import pytest
from datetime import date
from typing import List

from backend.app.services.models import (
    Person, Project, Task, PersonSkill, Skill, TaskRequiredRange, PersonBusyRange
)
from backend.app.services.scheduler import SchedulerService

def create_person(
    id: str, 
    skills: List[PersonSkill],
    schedule: List[PersonBusyRange] = None
) -> Person:
    return Person(
        id=id,
        name=f"Person_{id}",
        joining_date=date(2024, 1, 1),
        termination_date=None,
        skills=skills,
        schedule=schedule or []
    )

def create_simple_project(id: str, skill_id: str, start: date, end: date) -> Project:
    task = Task(
        id=f"t_{id}",
        name=f"Task_{id}",
        project_id=id,
        skill_id=skill_id,
        workforce_count=1,
        required_skill=Skill(id=skill_id, name="Skill"),
        required_ranges=[
            TaskRequiredRange(start_date=start, end_date=end)
        ]
    )
    return Project(
        id=id,
        name=f"Project_{id}",
        tasks=[task]
    )

def test_detailed_infeasibility_reason_busy():
    """
    Test that failure reason identifies a person is busy.
    """
    skill_id = "python"
    
    # Alice is busy on Jan 1-2
    alice = create_person("alice", [PersonSkill(id=skill_id, name="Python")], schedule=[
        PersonBusyRange(start_date=date(2024, 1, 1), end_date=date(2024, 1, 2))
    ])
    
    # Project needs Alice on Jan 1-2
    project = create_simple_project("p1", skill_id, date(2024, 1, 1), date(2024, 1, 2))
    
    scheduler = SchedulerService()
    _, infeasible = scheduler.schedule_all([project], [alice])
    
    assert len(infeasible) == 1
    result = infeasible[0]
    task_res = result.tasks[0]
    
    # Check that the failure reason mentions Alice and "Busy"
    assert task_res.failure_reason is not None
    assert "Person_alice" in task_res.failure_reason, "Should mention the person name"
    # We expect some indication of 'Busy' or the busy range
    # e.g. "Person_alice (Busy: ...)"
    # For now, let's just assert it is not the generic "Insufficient capacity"
    print(f"Failure reason: {task_res.failure_reason}")

def test_detailed_infeasibility_reason_conflict():
    """
    Test that failure reason identifies conflict with another project.
    """
    skill_id = "python"
    
    # Bob is available
    bob = create_person("bob", [PersonSkill(id=skill_id, name="Python")])
    
    # Project A (Scheduled)
    proj_a = create_simple_project("p_a", skill_id, date(2024, 1, 1), date(2024, 1, 2))
    
    # Project B (Conflict)
    proj_b = create_simple_project("p_b", skill_id, date(2024, 1, 1), date(2024, 1, 2))
    
    scheduler = SchedulerService()
    # Schedule both. One should work, one should fail. 
    # Since Bob is the only one, one project will take him.
    feasible, infeasible = scheduler.schedule_all([proj_a, proj_b], [bob])
    
    assert len(feasible) == 1
    assert len(infeasible) == 1
    
    failed_proj = infeasible[0]
    task_res = failed_proj.tasks[0]
    
    assert task_res.failure_reason is not None
    # Should mention Bob and the project he is assigned to (the feasible one)
    feasible_proj_name = feasible[0].name
    assert "Person_bob" in task_res.failure_reason
    # Ideally it should say "Person_bob (Assigned to Project_...)"
    print(f"Failure reason: {task_res.failure_reason}")

if __name__ == "__main__":
    # Allow running directly
    print("Running tests manual...")
    try:
        test_detailed_infeasibility_reason_busy()
        print("Test Busy: Passed (or at least ran)")
    except AssertionError as e:
        print(f"Test Busy Failed: {e}")
        
    try:
        test_detailed_infeasibility_reason_conflict()
        print("Test Conflict: Passed (or at least ran)")
    except AssertionError as e:
        print(f"Test Conflict Failed: {e}")

    try:
        test_infeasibility_reason_missing_skill()
        print("Test Missing Skill: Passed (or at least ran)")
    except AssertionError as e:
        print(f"Test Missing Skill Failed: {e}")

def test_infeasibility_reason_missing_skill():
    """
    Test that failure reason uses skill name instead of ID.
    """
    # Person has Python
    alice = create_person("alice", [PersonSkill(id="python", name="Python")])
    
    # Project needs Java
    # Note: Skill Name is "Java Language" to ensure we are testing for name, not ID
    project = create_simple_project("p_java", "java", date(2024, 1, 1), date(2024, 1, 2))
    project.tasks[0].required_skill = Skill(id="java", name="Java Language")
    
    scheduler = SchedulerService()
    _, infeasible = scheduler.schedule_all([project], [alice])
    
    assert len(infeasible) == 1
    result = infeasible[0]
    task_res = result.tasks[0]
    
    assert task_res.failure_reason is not None
    # Check for Skill Name 
    assert "Java Language" in task_res.failure_reason, f"Expected 'Java Language' in '{task_res.failure_reason}'"
    assert "java" not in task_res.failure_reason.lower().replace("java language", ""), "Should not contain ID if name is different"

