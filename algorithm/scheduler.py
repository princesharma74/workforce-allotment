from typing import List, Tuple
from .models import Project, Person, DateRange

class Scheduler:
    def schedule_all(self, projects: List[Project], people: List[Person]):
        feasible_projects = []
        infeasible_projects = []

        for project in projects:
            if self.schedule_project(project, people):
                feasible_projects.append(project)
            else:
                infeasible_projects.append(project)
        
        return feasible_projects, infeasible_projects

    def schedule_project(self, project: Project, people: List[Person]) -> bool:
        # Snapshot of people's schedules to rollback if project fails
        # Since deepcopy might be expensive, we can track changes.
        # However, for simplicity, let's try to assign all tasks.
        # If any task fails, we must rollback assignments for THIS project.
        
        assignments: List[Tuple[Person, List[DateRange]]] = []
        
        for task in project.tasks:
            assigned = False
            for person in people:
                if task.required_skill in person.skills and person.is_available(task.required_ranges):
                    # Assign
                    person.book(task.required_ranges)
                    task.assigned_person = person
                    assignments.append((person, task.required_ranges))
                    assigned = True
                    break
            
            if not assigned:
                # Project failed. Rollback.
                self.rollback(assignments)
                project.feasible = False
                project.failure_reason = f"Could not assign task: {task.name}"
                project.failed_tasks.append(task)
                return False
        
        return True

    def rollback(self, assignments: List[Tuple[Person, List[DateRange]]]):
        for person, ranges in assignments:
            for r in ranges:
                if r in person.schedule:
                    person.schedule.remove(r)
