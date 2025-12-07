from typing import List, Optional
from datetime import date
from sqlmodel import Field, SQLModel, Relationship

# Link table for Person-Skill many-to-many relationship
class PersonSkillLink(SQLModel, table=True):
    person_id: Optional[int] = Field(default=None, foreign_key="person.id", primary_key=True)
    skill_id: Optional[int] = Field(default=None, foreign_key="skill.id", primary_key=True)

class Skill(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    
    people: List["Person"] = Relationship(back_populates="skills", link_model=PersonSkillLink)
    tasks: List["Task"] = Relationship(back_populates="required_skill")

class Person(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    joining_date: date
    termination_date: Optional[date] = None
    
    skills: List[Skill] = Relationship(back_populates="people", link_model=PersonSkillLink)
    assigned_tasks: List["Task"] = Relationship(back_populates="assigned_person")
    # Busy ranges (manual schedule)
    schedule: List["PersonBusyRange"] = Relationship(back_populates="person")

class PersonBusyRange(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    person_id: int = Field(foreign_key="person.id")
    start_date: date
    end_date: date
    
    person: Person = Relationship(back_populates="schedule")

    def overlaps(self, start: date, end: date) -> bool:
        return max(self.start_date, start) <= min(self.end_date, end)

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    tasks: List["Task"] = Relationship(back_populates="project")

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    project_id: int = Field(foreign_key="project.id")
    skill_id: int = Field(foreign_key="skill.id")
    assigned_person_id: Optional[int] = Field(default=None, foreign_key="person.id")

    
    project: Project = Relationship(back_populates="tasks")
    required_skill: Skill = Relationship(back_populates="tasks")
    assigned_person: Optional[Person] = Relationship(back_populates="assigned_tasks")
    
    required_ranges: List["TaskRequiredRange"] = Relationship(back_populates="task")

class TaskRequiredRange(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id")
    start_date: date
    end_date: date
    
    task: Task = Relationship(back_populates="required_ranges")

    def overlaps(self, start: date, end: date) -> bool:
        return max(self.start_date, start) <= min(self.end_date, end)
