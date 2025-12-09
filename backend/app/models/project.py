from typing import List, Optional
from datetime import date
import uuid
from sqlmodel import Field, SQLModel, Relationship
from .enums import ProjectStatus, DesignType, PackageType

class Project(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True)
    tapeout_date: Optional[date] = None
    compilers_count: int = Field(default=0)
    instances_per_compiler: int = Field(default=0)
    duration_weeks: int = Field(default=0)
    
    design_type: Optional[DesignType] = Field(default=None)
    package_type: Optional[PackageType] = Field(default=None)
    status: ProjectStatus = Field(default=ProjectStatus.BACKLOG)
    
    tasks: List["Task"] = Relationship(back_populates="project")
