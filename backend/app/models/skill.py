from typing import List, Optional
import uuid
from sqlmodel import Field, SQLModel, Relationship
from .links import PersonSkillLink

class Skill(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True)
    
    # Use overlaps to silence SAWarnings
    # Warning said: overlaps="skill" and overlaps="person" ... wait, let's include all involved relationships
    people: List["Person"] = Relationship(back_populates="skills", link_model=PersonSkillLink, sa_relationship_kwargs={"overlaps": "person_links,skill,person"})
    tasks: List["Task"] = Relationship(back_populates="required_skill")
    person_links: List["PersonSkillLink"] = Relationship(back_populates="skill", sa_relationship_kwargs={"overlaps": "people,skill"})
