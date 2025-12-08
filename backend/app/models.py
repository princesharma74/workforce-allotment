from typing import List, Optional
from datetime import date
import uuid
from sqlmodel import Field, SQLModel, Relationship

# Link table for Person-Skill many-to-many relationship
class PersonSkillLink(SQLModel, table=True):
    person_id: Optional[str] = Field(default=None, foreign_key="person.id", primary_key=True)
    skill_id: Optional[str] = Field(default=None, foreign_key="skill.id", primary_key=True)
    efficiency: int = Field(default=1)

    person: "Person" = Relationship(back_populates="skill_links")
    skill: "Skill" = Relationship(back_populates="person_links")

# Link table for Task-Person many-to-many relationship (Assignments)
class TaskPersonLink(SQLModel, table=True):
    task_id: Optional[str] = Field(default=None, foreign_key="task.id", primary_key=True)
    person_id: Optional[str] = Field(default=None, foreign_key="person.id", primary_key=True)

class Skill(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True)
    
    # Use overlaps to silence SAWarnings
    # Warning said: overlaps="skill" and overlaps="person" ... wait, let's include all involved relationships
    people: List["Person"] = Relationship(back_populates="skills", link_model=PersonSkillLink, sa_relationship_kwargs={"overlaps": "person_links,skill,person"})
    tasks: List["Task"] = Relationship(back_populates="required_skill")
    person_links: List["PersonSkillLink"] = Relationship(back_populates="skill", sa_relationship_kwargs={"overlaps": "people,skill"})

class Person(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True)
    joining_date: date
    termination_date: Optional[date] = None
    
    # Warning said: overlaps="person" and "person_links,skill"
    # The conflict is usually between the relationship to the link table vs the relationship THROUGH the link table
    skills: List[Skill] = Relationship(back_populates="people", link_model=PersonSkillLink, sa_relationship_kwargs={"overlaps": "skill_links,person,skill,person_links"})
    skill_links: List["PersonSkillLink"] = Relationship(back_populates="person", sa_relationship_kwargs={"overlaps": "skills,person,people"})
    assigned_tasks: List["Task"] = Relationship(back_populates="assignees", link_model=TaskPersonLink)
    # Busy ranges (manual schedule)
    schedule: List["PersonBusyRange"] = Relationship(back_populates="person")

class PersonBusyRange(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    person_id: str = Field(foreign_key="person.id")
    start_date: date
    end_date: date
    
    person: Person = Relationship(back_populates="schedule")

    def overlaps(self, start: date, end: date) -> bool:
        return max(self.start_date, start) <= min(self.end_date, end)

class Project(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True)
    tasks: List["Task"] = Relationship(back_populates="project")

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
