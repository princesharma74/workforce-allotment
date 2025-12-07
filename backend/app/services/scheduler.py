from typing import List, Tuple, Dict
from sqlmodel import Session, select
from ..models import Project, Person, Task, TaskRequiredRange, PersonBusyRange
from ..schemas import ProjectAnalysisResult, TaskAnalysisResult, TaskRead, SkillRead

class SchedulerService:
    def __init__(self, session: Session):
        self.session = session

    def schedule_all(self, commit: bool = True) -> Tuple[List[ProjectAnalysisResult], List[ProjectAnalysisResult]]:
        # Fetch all projects and people
        projects = self.session.exec(select(Project)).all()
        people = self.session.exec(select(Person)).all()
        
        feasible_results = []
        infeasible_results = []
        
        # We need to clear previous assignments first? 
        # For now, let's assume we are scheduling from scratch or on top of existing.
        # Ideally, we should reset assignments for the projects being scheduled.
        
        for project in projects:
            # We will build an analysis result for each project
            # But we ALSO might modify the DB objects if commit=True
            
            project_feasible = True
            project_failure = None
            task_results = []
            
            # Reset tasks in memory for logic
            for task in project.tasks:
                task.assigned_person_id = None
                self.session.add(task)
            
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
            
            # If we are committing, we leave the valid assignments on the objects. 
            # If not committing (dry run), we shouldn't commit anyway, but objects are modified in session.
            # The caller handles session commit/rollback.
            
        if commit:
            self.session.commit()
        else:
            # Rollback all assignments to ensure no side effects in dry_run
            # We already rolled back failure projects. Now rollback successful ones too.
            all_assignments_to_rollback = []
            for res in feasible_results:
                 # Logic to find assignments - or just simple: reload tasks or iterate projects again?
                 # Easier: track all assignments during the process.
                 pass
            # Actually easier: The session has modified objects.
            # If we don't commit, the DB isn't touched.
            # But the Objects in memory are modified.
            # We should reset them if we want to be clean.
            for project in projects:
                for task in project.tasks:
                     self.session.refresh(task) # This might not work if transaction is active?
                     # Better: manually reset
                     task.assigned_person_id = None 
                     # Wait, we want to reset to state BEFORE we started? 
                     # The code assumes we start from scratch (line 32: task.assigned_person_id = None).
                     # So resetting to None is correct behavior for "cleaning up".
                     task.assigned_person_id = None
                     self.session.add(task)
            
            # Or safer: session.rollback() if we can?
            # session.rollback() might close transaction.
            pass

        return feasible_results, infeasible_results

    def _build_result(self, project: Project, feasible: bool, failure_reason: str, task_failures: Dict[int, str]) -> ProjectAnalysisResult:
        tasks_analyzed = []
        from backend.app.schemas import DateRange
        for t in project.tasks:
            # Re-construct necessary read data
            req_ranges = [DateRange(start=r.start_date, end=r.end_date) for r in t.required_ranges]
            
            tasks_analyzed.append(TaskAnalysisResult(
                id=t.id,
                name=t.name,
                project_id=project.id,
                skill_id=t.skill_id,
                assigned_person_id=t.assigned_person_id,
                required_skill=SkillRead(id=t.required_skill.id, name=t.required_skill.name),
                required_ranges=req_ranges,
                failure_reason=task_failures.get(t.id)
            ))
            
        return ProjectAnalysisResult(
            id=project.id,
            name=project.name,
            feasible=feasible,
            failure_reason=failure_reason,
            tasks=tasks_analyzed
        )

    def schedule_project(self, project: Project, people: List[Person]) -> Tuple[bool, List[Tuple[Person, Task]], Dict[int, str]]:
        assignments: List[Tuple[Person, Task]] = []
        task_failures: Dict[int, str] = {}
        all_assigned = True
        
        for task in project.tasks:
            assigned = False
            for person in people:
                if self.can_assign(person, task):
                    # Assign
                    task.assigned_person_id = person.id
                    self.session.add(task)
                    # Update temporary state for checks
                    person.assigned_tasks.append(task)
                    
                    assignments.append((person, task))
                    assigned = True
                    break
            
            if not assigned:
                task_failures[task.id] = f"No available person with skill '{task.required_skill.name}'"
                all_assigned = False
        
        return all_assigned, assignments, task_failures

    def can_assign(self, person: Person, task: Task) -> bool:
        # Check Skill
        person_skill_ids = {s.id for s in person.skills}
        if task.skill_id not in person_skill_ids:
            return False
            
        # Check Availability
        for req_range in task.required_ranges:
            # Check employment
            if req_range.start_date < person.joining_date:
                return False
            if person.termination_date and req_range.end_date > person.termination_date:
                return False
            
            # Check manual schedule
            for busy in person.schedule:
                if busy.overlaps(req_range.start_date, req_range.end_date):
                    return False
            
            # Check existing tasks (including those assigned in this session)
            for assigned_task in person.assigned_tasks:
                # Skip the current task itself if it's somehow already there (shouldn't be)
                if assigned_task.id == task.id:
                    continue
                    
                for assigned_range in assigned_task.required_ranges:
                    if assigned_range.overlaps(req_range.start_date, req_range.end_date):
                        return False
                        
        return True

    def rollback(self, assignments: List[Tuple[Person, Task]]):
        for person, task in assignments:
            task.assigned_person_id = None
            if task in person.assigned_tasks:
                person.assigned_tasks.remove(task)
