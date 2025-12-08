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
    id: str

class PersonSkillCreate(SQLModel):
    name: str
    efficiency: int = 1

class PersonSkillRead(SkillRead):
    efficiency: int = 1

class PersonBase(SQLModel):
    name: str
    joining_date: date
    termination_date: Optional[date] = None

class PersonCreate(PersonBase):
    skills: List[PersonSkillCreate] = []
    busy_ranges: List[DateRange] = [] 

class PersonRead(PersonBase):
    id: str
    skills: List[PersonSkillRead] = []
    busy_ranges: List[DateRange] = [] 

class ProjectBase(SQLModel):
    name: str

class TaskCreateInput(SQLModel):
    name: str
    skill_name: str
    required_ranges: List[DateRange] = []
    workforce_count: int = 1

class ProjectCreate(ProjectBase):
    tasks: List[TaskCreateInput] 

class TaskRead(SQLModel):
    id: str
    name: str
    project_id: str
    skill_id: str
    # assignees: List["PersonRead"] # Circular dependency issue, leaving out details or using base
    assignees: List[PersonRead] = []
    required_skill: SkillRead
    required_ranges: List[DateRange]
    workforce_count: int

class ProjectRead(ProjectBase):
    id: str
    tasks: List[TaskRead] = []

class TaskAnalysisResult(TaskRead):
    failure_reason: Optional[str] = None

class ProjectAnalysisResult(ProjectRead):
    feasible: bool
    failure_reason: Optional[str] = None
    tasks: List[TaskAnalysisResult]

class TaskAssignment(SQLModel):
    task_id: str
    person_id: str

class BulkAssignmentRequest(SQLModel):
    assignments: List[TaskAssignment]

class SkillUpdate(SQLModel):
    name: Optional[str] = None

class PersonUpdate(SQLModel):
    name: Optional[str] = None
    joining_date: Optional[date] = None
    termination_date: Optional[date] = None
    skills: Optional[List[PersonSkillCreate]] = None
    busy_ranges: Optional[List[DateRange]] = None

class ProjectUpdate(SQLModel):
    name: Optional[str] = None

class TaskUpdate(SQLModel):
    name: Optional[str] = None
    skill_name: Optional[str] = None
    workforce_count: Optional[int] = None
    required_ranges: Optional[List[DateRange]] = None
