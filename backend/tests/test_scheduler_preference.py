import pytest
from datetime import date
from typing import List

from backend.app.services.models import (
    Person, Project, Task, PersonSkill, Skill, TaskRequiredRange
)
from backend.app.services.scheduler import SchedulerService, SchedulerConfig

def create_person(
    id: str, 
    skills: List[PersonSkill]
) -> Person:
    return Person(
        id=id,
        name=f"Person {id}",
        joining_date=date(2023, 1, 1),
        termination_date=None,
        skills=skills,
        schedule=[]
    )

def create_simple_project(id: str, skill_id: str, workforce: int = 1) -> Project:
    task = Task(
        id=f"t_{id}",
        name=f"Task {id}",
        project_id=id,
        skill_id=skill_id,
        workforce_count=workforce,
        required_skill=Skill(id=skill_id, name="Test Skill"),
        required_ranges=[
            TaskRequiredRange(
                start_date=date(2023, 1, 10),
                end_date=date(2023, 1, 15)
            )
        ]
    )
    return Project(
        id=id,
        name=f"Project {id}",
        tasks=[task]
    )

def test_preference_optimization():
    """
    Test that scheduler prefers person with higher preference score
    when efficiency is equal.
    """
    # 2 people with same skill and efficiency
    # P1: Preference 1 (default)
    # P2: Preference 5
    
    skill_id = "python"
    
    p1 = create_person("p1", [PersonSkill(id=skill_id, name="Python", efficiency=1, preference_score=1)])
    p2 = create_person("p2", [PersonSkill(id=skill_id, name="Python", efficiency=1, preference_score=5)])
    
    project = create_simple_project("proj1", skill_id, workforce=1)
    
    scheduler = SchedulerService()
    feasible, _ = scheduler.schedule_all([project], [p1, p2])
    
    assert len(feasible) == 1
    task_result = feasible[0].tasks[0]
    
    # Must pick P2 due to higher preference
    assert len(task_result.assignees) == 1
    assert task_result.assignees[0].id == "p2"

def test_backward_compatibility():
    """
    Test that without preference scores (all default 1), 
    scheduler works normally (picks first/arbitrary but valid).
    """
    skill_id = "java"
    
    # Both default preference = 1
    p1 = create_person("p1", [PersonSkill(id=skill_id, name="Java", efficiency=1)])
    p2 = create_person("p2", [PersonSkill(id=skill_id, name="Java", efficiency=1)])
    
    project = create_simple_project("proj_legacy", skill_id, workforce=1)
    
    scheduler = SchedulerService()
    feasible, _ = scheduler.schedule_all([project], [p1, p2])
    
    assert len(feasible) == 1
    task_result = feasible[0].tasks[0]
    assert len(task_result.assignees) == 1
    assert task_result.assignees[0].id in ["p1", "p2"]

def test_efficiency_over_preference():
    """
    Test that scheduler prioritizes minimizing assignments (efficiency)
    over maximizing preference score.
    """
    # Task requires workforce 2
    
    # P1: Efficiency 2, Preference 1 (Can do it alone) -> Score: -1M (1 assign) + 1K (pref)
    # P2: Efficiency 1, Preference 10 
    # P3: Efficiency 1, Preference 10
    # (P2+P3): Score: -2M (2 assigns) + 20K (pref)
    
    # Delta: Efficiency benefit (1M) >> Preference benefit (19K)
    # Should pick P1
    
    skill_id = "cpp"
    
    p1 = create_person("p1_eff", [PersonSkill(id=skill_id, name="C++", efficiency=2, preference_score=1)])
    p2 = create_person("p2_pref", [PersonSkill(id=skill_id, name="C++", efficiency=1, preference_score=10)])
    p3 = create_person("p3_pref", [PersonSkill(id=skill_id, name="C++", efficiency=1, preference_score=10)])
    
    project = create_simple_project("proj_eff", skill_id, workforce=2)
    # Ensure task allows efficiency > 1 assignment
    
    scheduler = SchedulerService()
    feasible, _ = scheduler.schedule_all([project], [p1, p2, p3])
    
    assert len(feasible) == 1
    task_result = feasible[0].tasks[0]
    
    # Should assign only P1
    assert len(task_result.assignees) == 1
    assert task_result.assignees[0].id == "p1_eff"
