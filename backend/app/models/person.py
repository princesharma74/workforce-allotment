from typing import List, Optional
from datetime import date
import uuid
from sqlmodel import Field, SQLModel, Relationship
from .links import PersonSkillLink, TaskPersonLink
# Forward reference to Skill is needed for type hinting, but circular import might be an issue if we import Skill directly here at top level if Skill imports Person.
# So we use string forward references.

class Person(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True)
    email: Optional[str] = None
    joining_date: date
    termination_date: Optional[date] = None
    
    # Warning said: overlaps="person" and "person_links,skill"
    # The conflict is usually between the relationship to the link table vs the relationship THROUGH the link table
    skills: List["Skill"] = Relationship(back_populates="people", link_model=PersonSkillLink, sa_relationship_kwargs={"overlaps": "skill_links,person,skill,person_links"})
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
