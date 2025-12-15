from typing import List, Tuple, Dict, Optional
from datetime import timedelta
from .models import (
    Project, Person, Task, 
    ProjectAnalysisResult, TaskAnalysisResult, DateRange, PersonRead, SkillRead
)

class SchedulerService:
    def __init__(self):
        pass

    def schedule_all(self, projects: List[Project], people: List[Person]) -> Tuple[List[ProjectAnalysisResult], List[ProjectAnalysisResult]]:
        # projects and people are now lists of Dataclasses, not SQLModel objects attached to a session.
        
        feasible_results = []
        infeasible_results = []
        
        for project in projects:
            # We will build an analysis result for each project
            
            project_feasible = True
            project_failure = None
            
            # Note: We need to remove these tasks from people's assigned_tasks if they are already there 
            # (i.e. we are rescheduling this project).
            # Otherwise, check_assignment_viability will see them as busy with *this* task.
            ids_to_clear = {t.id for t in project.tasks}
            for person in people:
                # Rebuild assigned_tasks filtering out current project's tasks
                person.assigned_tasks = [t for t in person.assigned_tasks if t.id not in ids_to_clear]
            
            # Reset tasks in memory for logic
            for task in project.tasks:
                task.assignees = []
            
            # Try to schedule
            success, assignments, failures = self.schedule_project(project, people)
            
            if success:
                project_feasible = True
                feasible_results.append(self._build_result(project, True, None, failures))
            else:
                project_feasible = False
                infeasible_results.append(self._build_result(project, False, "One or more tasks could not be assigned.", failures))
            
            # If not feasible, we rollback assignments for this project
            if not project_feasible:
                self.rollback(assignments)
            
            # If feasible, we leave the assignments in place on the objects. 
            
        return feasible_results, infeasible_results

    def _build_result(self, project: Project, feasible: bool, failure_reason: str, task_failures: Dict[int, str]) -> ProjectAnalysisResult:
        tasks_analyzed = []
        for t in project.tasks:
            req_ranges = [DateRange(start_date=r.start_date, end_date=r.end_date) for r in t.required_ranges]
            
            # Construct assignees list
            assignees_read = []
            for p in t.assignees:
                assignees_read.append(PersonRead(
                    id=p.id,
                    name=p.name,
                    joining_date=p.joining_date,
                    termination_date=p.termination_date,
                    skills=[SkillRead(id=s.id, name=s.name, efficiency=s.efficiency) for s in p.skills],
                    busy_ranges=[DateRange(start_date=b.start_date, end_date=b.end_date) for b in p.schedule]
                ))

            tasks_analyzed.append(TaskAnalysisResult(
                id=t.id,
                name=t.name,
                project_id=project.id,
                skill_id=t.skill_id,
                assignees=assignees_read,
                required_skill=SkillRead(id=t.required_skill.id, name=t.required_skill.name),
                required_ranges=req_ranges,
                workforce_count=t.workforce_count,
                failure_reason=task_failures.get(t.id)
            ))
            
        return ProjectAnalysisResult(
            id=project.id,
            name=project.name,
            tasks=tasks_analyzed,
            feasible=feasible,
            failure_reason=failure_reason
        )

    def schedule_project(self, project: Project, people: List[Person]) -> Tuple[bool, List[Tuple[Person, Task]], Dict[int, str]]:
        assignments: List[Tuple[Person, Task]] = []
        task_failures: Dict[int, str] = {}
        all_assigned = True
        
        for task in project.tasks:
            needed = task.workforce_count
            current_efficiency = 0
            
            rejection_stats = {}
            total_people_checked = 0
            
            # Try to find people to satisfy 'needed' efficiency
            # Sort people by number of skills (ascending) to use less versatile people first
            # This helps avoid using a multi-skilled person for a task that a single-skilled person could do
            sorted_people = sorted(people, key=lambda p: len(p.skills))
            
            for person in sorted_people:
                if current_efficiency >= needed:
                    break
                
                total_people_checked += 1
                # Check if person can check the task
                can_assign, reason = self.check_assignment_viability(person, task)
                
                if can_assign:
                    # Get efficiency
                    person_skill = next((s for s in person.skills if s.id == task.skill_id), None)
                    efficiency = getattr(person_skill, 'efficiency', 1) if person_skill else 0
                    
                    # Assign
                    task.assignees.append(person)
                    person.assigned_tasks.append(task)
                    
                    assignments.append((person, task))
                    current_efficiency += efficiency
                else:
                    # Collect rejection reason
                    if reason not in rejection_stats:
                        rejection_stats[reason] = 0
                    rejection_stats[reason] += 1
            
            if current_efficiency < needed:
                # Build detailed failure message
                reasons_str = "; ".join([f"{r}: {c}" for r, c in rejection_stats.items()])
                msg = f"Insufficient workforce. Needed efficiency {needed}, found {current_efficiency}. "
                msg += f"Checked {total_people_checked} people. "
                if reasons_str:
                    msg += f"Rejections: [{reasons_str}]"
                else:
                    msg += "No available people found."

                task_failures[task.id] = msg
                all_assigned = False
        
        return all_assigned, assignments, task_failures

    def check_assignment_viability(self, person: Person, task: Task) -> Tuple[bool, Optional[str]]:
        # Check Skill
        person_skill = next((s for s in person.skills if s.id == task.skill_id), None)
        if not person_skill:
            return False, f"Missing skill '{task.required_skill.name}'"
            
        efficiency = getattr(person_skill, 'efficiency', 1)
            
        # Check Availability
        for req_range in task.required_ranges:
            # Check employment
            if req_range.start_date < person.joining_date:
                return False, f"Not employed at start ({person.joining_date})"
            if person.termination_date and req_range.end_date > person.termination_date:
                return False, f"Terminated before end ({person.termination_date})"
            
            # Check manual schedule
            for busy in person.schedule:
                if busy.overlaps(req_range.start_date, req_range.end_date):
                    return False, "Busy in manual schedule"
            
        # Check Concurrency with specific attention to Efficiency
        interfering_ranges = []
        
        for assigned_task in person.assigned_tasks:
            if assigned_task.id == task.id:
                continue
                
            is_same_skill = (assigned_task.skill_id == task.skill_id)
            
            # Check overlapping ranges
            for ar in assigned_task.required_ranges:
                overlaps = False
                for nr in task.required_ranges:
                    if ar.overlaps(nr.start_date, nr.end_date):
                        overlaps = True
                        break
                
                if overlaps:
                    if not is_same_skill:
                        return False, f"Conflict with task '{assigned_task.name}' (different skill)"
                    interfering_ranges.append(ar)
        
        if not interfering_ranges:
             return True, None

        if efficiency == 1:
            return False, "Already assigned overlapping task (Efficiency 1)"
            
        # Efficiency > 1: Check Max Overlap
        # We need to verify that adding the new task's ranges doesn't exceed efficiency
        for nr in task.required_ranges:
            # Find relevant ranges for this specific new range
            relevant = [r for r in interfering_ranges if r.overlaps(nr.start_date, nr.end_date)]
            
            if not relevant:
                continue
                
            events = []
            # Add new range event
            events.append((nr.start_date, 1))
            events.append((nr.end_date + timedelta(days=1), -1))
            
            # Add existing relevant ranges
            for r in relevant:
                events.append((r.start_date, 1))
                events.append((r.end_date + timedelta(days=1), -1))
            
            events.sort(key=lambda x: (x[0], x[1])) 
            
            max_load = 0
            current_load = 0
            for _, change in events:
                current_load += change
                max_load = max(max_load, current_load)
                
            if max_load > efficiency:
                return False, f"Efficiency limit exceeded (Max {efficiency}, Needs {max_load})"
                        
        return True, None

    def rollback(self, assignments: List[Tuple[Person, Task]]):
        for person, task in assignments:
            if person in task.assignees:
                task.assignees.remove(person)
            if task in person.assigned_tasks:
                person.assigned_tasks.remove(task)
