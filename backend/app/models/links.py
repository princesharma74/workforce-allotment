from typing import Optional
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
