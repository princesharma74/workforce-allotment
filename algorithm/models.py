from dataclasses import dataclass, field
from datetime import date
from typing import Set, List, Optional

@dataclass(frozen=True)
class Skill:
    name: str

@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def overlaps(self, other: 'DateRange') -> bool:
        return max(self.start, other.start) <= min(self.end, other.end)

@dataclass
class Task:
    name: str
    required_skill: Skill
    required_ranges: List[DateRange]
    assigned_person: Optional['Person'] = None
    project: Optional['Project'] = field(default=None, repr=False)
    
@dataclass
class Person:
    name: str
    skills: Set[Skill]
    schedule: List[DateRange] = field(default_factory=list)
    joining_date: date = field(default_factory=date.today)
    termination_date: Optional[date] = None
    assigned_tasks: List[Task] = field(default_factory=list)

    def is_available(self, ranges: List[DateRange]) -> bool:
        for needed_range in ranges:
            # Check employment period
            if needed_range.start < self.joining_date:
                return False
            if self.termination_date and needed_range.end > self.termination_date:
                return False

            # Check schedule conflicts (Manually added busy periods)
            for busy_range in self.schedule:
                if needed_range.overlaps(busy_range):
                    return False
            
            # Check availability against assigned tasks
            for task in self.assigned_tasks:
                for task_range in task.required_ranges:
                     if needed_range.overlaps(task_range):
                         return False
                         
        return True

    def book(self, ranges: List[DateRange]):
        # Deprecated: usage should move to explicit task assignment or manual schedule entry
        self.schedule.extend(ranges)
        
    def assign_task(self, task: Task):
        self.assigned_tasks.append(task)
        task.assigned_person = self

@dataclass
class Project:
    name: str
    tasks: List[Task]
    feasible: bool = True
    failure_reason: Optional[str] = None
    failed_tasks: List[Task] = field(default_factory=list)

    def __post_init__(self):
        for task in self.tasks:
            task.project = self
