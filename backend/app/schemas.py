from typing import List, Optional
from datetime import date
from sqlmodel import SQLModel
from .models import Skill, PersonBusyRange, TaskRequiredRange

# Shared properties
class DateRange(SQLModel):
    start: date
    end: date

class SkillBase(SQLModel):
    name: str

class SkillCreate(SkillBase):
    pass

class SkillRead(SkillBase):
    id: int

class PersonBase(SQLModel):
    name: str
    joining_date: date
    termination_date: Optional[date] = None

class PersonCreate(PersonBase):
    skill_names: List[str] = []
    busy_ranges: List[DateRange] = [] 

class PersonRead(PersonBase):
    id: int
    skills: List[SkillRead] = []
    busy_ranges: List[DateRange] = [] 

class ProjectBase(SQLModel):
    name: str

class TaskCreateInput(SQLModel):
    name: str
    skill_name: str
    required_ranges: List[DateRange] = []

class ProjectCreate(ProjectBase):
    tasks: List[TaskCreateInput] 

class TaskRead(SQLModel):
    id: int
    name: str
    project_id: int
    skill_id: int
    assigned_person_id: Optional[int]
    required_skill: SkillRead
    required_ranges: List[DateRange]

class ProjectRead(ProjectBase):
    id: int
    tasks: List[TaskRead] = []

class TaskAnalysisResult(TaskRead):
    failure_reason: Optional[str] = None

class ProjectAnalysisResult(ProjectRead):
    feasible: bool
    failure_reason: Optional[str] = None
    tasks: List[TaskAnalysisResult]

class TaskAssignment(SQLModel):
    task_id: int
    person_id: int

class BulkAssignmentRequest(SQLModel):
    assignments: List[TaskAssignment]

class SkillUpdate(SQLModel):
    name: Optional[str] = None

class PersonUpdate(SQLModel):
    name: Optional[str] = None
    joining_date: Optional[date] = None
    termination_date: Optional[date] = None
    skill_names: Optional[List[str]] = None
    busy_ranges: Optional[List[DateRange]] = None

class ProjectUpdate(SQLModel):
    name: Optional[str] = None

class TaskUpdate(SQLModel):
    name: Optional[str] = None
    skill_name: Optional[str] = None
    required_ranges: Optional[List[DateRange]] = None
