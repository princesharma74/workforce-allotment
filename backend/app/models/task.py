from typing import List, Optional
from datetime import date
import uuid
from sqlmodel import Field, SQLModel, Relationship
from .project import Project
from .skill import Skill
from .person import Person
from .links import TaskPersonLink

class Task(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    project_id: str = Field(foreign_key="project.id")
    skill_id: str = Field(foreign_key="skill.id")
    workforce_count: int = Field(default=1)

    project: Project = Relationship(back_populates="tasks")
    required_skill: Skill = Relationship(back_populates="tasks")
    assignees: List[Person] = Relationship(back_populates="assigned_tasks", link_model=TaskPersonLink)
    
    required_ranges: List["TaskRequiredRange"] = Relationship(back_populates="task")

class TaskRequiredRange(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    task_id: str = Field(foreign_key="task.id")
    start_date: date
    end_date: date
    
    task: Task = Relationship(back_populates="required_ranges")

    def overlaps(self, start: date, end: date) -> bool:
        return max(self.start_date, start) <= min(self.end_date, end)
