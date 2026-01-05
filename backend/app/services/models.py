from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date

@dataclass
class Skill:
    id: str
    name: str

@dataclass
class PersonSkill(Skill):
    efficiency: int = 1
    preference_score: int = 1

@dataclass
class DateRange:
    start_date: date
    end_date: date

    def overlaps(self, start: date, end: date) -> bool:
        return max(self.start_date, start) <= min(self.end_date, end)

@dataclass
class PersonBusyRange(DateRange):
    id: Optional[str] = None
    person_id: Optional[str] = None

@dataclass
class TaskRequiredRange(DateRange):
    id: Optional[str] = None
    task_id: Optional[str] = None

@dataclass
class Person:
    id: str
    name: str
    joining_date: date
    termination_date: Optional[date]
    skills: List[PersonSkill]
    schedule: List[PersonBusyRange]
    assigned_tasks: List["Task"] = field(default_factory=list)

@dataclass
class Task:
    id: str
    name: str
    project_id: str
    skill_id: str
    workforce_count: int
    required_skill: Skill
    required_ranges: List[TaskRequiredRange]
    assignees: List[Person] = field(default_factory=list)

@dataclass
class Project:
    id: str
    name: str
    tasks: List[Task]

# --- Result Dataclasses (Replacing Schemas) ---

@dataclass
class SkillRead:
    id: str
    name: str
    efficiency: int = 1
    preference_score: int = 1

@dataclass
class PersonRead:
    id: str
    name: str
    joining_date: date
    termination_date: Optional[date]
    skills: List[SkillRead]
    busy_ranges: List[DateRange]

@dataclass
class TaskAnalysisResult:
    id: str
    name: str
    project_id: str
    skill_id: str
    assignees: List[PersonRead]
    required_skill: SkillRead
    required_ranges: List[DateRange]
    workforce_count: int
    failure_reason: Optional[str] = None

@dataclass
class ProjectAnalysisResult:
    id: str
    name: str
    tasks: List[TaskAnalysisResult]
    feasible: bool
    failure_reason: Optional[str] = None
