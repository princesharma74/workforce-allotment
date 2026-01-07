"""
Workforce Scheduling Service using Google OR-Tools CP-SAT Solver.

This module provides an optimized scheduler that assigns tasks to people while:
- Maximizing the number of completed projects
- Minimizing the number of assignments (prefer fewer, more efficient workers)
- Balancing workload across the workforce
- Respecting constraints like skills, availability, and employment dates
"""

from typing import List, Tuple, Dict, Optional, Set
from datetime import date
from dataclasses import dataclass
from ortools.sat.python import cp_model

from .models import (
    Project, Person, Task,
    ProjectAnalysisResult, TaskAnalysisResult, DateRange, PersonRead, SkillRead
)


@dataclass
class SchedulerConfig:
    """Configuration for the scheduler optimization."""
    
    # Objective function weights
    project_weight: int = 1_000_000_000_000  # Maximize projects (highest priority)
    assignment_cost: int = 1_000_000          # Minimize assignments (prefer efficiency)
    preference_weight: int = 1_000            # Maximize preference (tertiary priority)
    workload_cost: int = 1                    # Minimize workload variance (balance)
    
    # Solver parameters
    num_workers: int = 8                      # Parallel search workers
    max_time_seconds: float = 60.0           # Maximum solve time
    
    # Time window
    fallback_min_date: date = date(2020, 1, 1)


@dataclass
class TimeWindow:
    """Represents the scheduling time window."""
    min_date: date
    start_day: int  # Relative to min_date
    end_day: int    # Relative to min_date
    
    def date_to_index(self, d: date) -> int:
        """Convert a date to an integer index relative to min_date."""
        return (d - self.min_date).days
    
    def get_overlap_days(self, start_idx: int, end_idx: int) -> int:
        """Calculate overlap between a range and the active window."""
        s = max(start_idx, self.start_day)
        e = min(end_idx, self.end_day + 1)
        return max(0, e - s)


@dataclass
class PersonSkillMap:
    """Efficient lookup for person skills and efficiencies."""
    skill_to_efficiency: Dict[str, int]  # skill_id -> efficiency
    skill_to_preference: Dict[str, int]  # skill_id -> preference

    
    def has_skill(self, skill_id: str) -> bool:
        """Check if person has a skill."""
        return skill_id in self.skill_to_efficiency
    
    def get_efficiency(self, skill_id: str) -> int:
        """Get efficiency for a skill (default 1)."""
        return self.skill_to_efficiency.get(skill_id, 1)

    def get_preference(self, skill_id: str) -> int:
        """Get preference for a skill (default 1)."""
        return self.skill_to_preference.get(skill_id, 1)


@dataclass
class TaskGeometry:
    """Precomputed task time ranges and load."""
    ranges: List[Tuple[int, int]]  # List of (start_idx, end_idx) exclusive
    total_load: int                 # Total days in active window


@dataclass
class AssignmentCandidate:
    """Represents a potential task assignment to a person."""
    task: Task
    var: cp_model.IntVar
    geometry: TaskGeometry


class SchedulerService:
    """
    Service for optimally scheduling tasks to people using constraint programming.
    
    The scheduler uses Google OR-Tools CP-SAT solver to find the optimal assignment
    that maximizes completed projects while balancing workload.
    """
    
    def __init__(self, config: Optional[SchedulerConfig] = None):
        """
        Initialize the scheduler service.
        
        Args:
            config: Optional configuration for optimization parameters
        """
        self.config = config or SchedulerConfig()
    
    def schedule_all(
        self, 
        projects: List[Project], 
        people: List[Person]
    ) -> Tuple[List[ProjectAnalysisResult], List[ProjectAnalysisResult]]:
        """
        Schedule all projects optimally across available workforce.
        
        Args:
            projects: List of projects with tasks to schedule
            people: List of available workforce
            
        Returns:
            Tuple of (feasible_projects, infeasible_projects)
        """
        # Initialize the constraint programming model
        model = cp_model.CpModel()
        
        # Step 1: Compute time window
        time_window = self._compute_time_window(projects, people)
        
        # Step 2: Build skill maps for efficient lookup
        skill_maps = self._build_skill_maps(people)
        
        # Step 3: Create project variables
        project_vars = self._create_project_variables(model, projects)
        
        # Step 4: Create assignment variables and precompute task geometry
        assignment_vars, person_assignments = self._create_assignment_variables(
            model, projects, people, skill_maps, time_window
        )
        
        # Step 5: Add fulfillment constraints (tasks must be completed)
        self._add_fulfillment_constraints(
            model, projects, people, project_vars, assignment_vars, skill_maps
        )
        
        # Step 6: Add interval constraints (no conflicts, respect efficiency)
        workload_vars = self._add_interval_constraints(
            model, people, person_assignments, skill_maps, time_window, projects
        )
        
        # Step 7: Define objective function
        self._define_objective(model, project_vars, assignment_vars, workload_vars, projects, skill_maps)
        
        # Step 8: Solve the model
        solver = self._create_solver()
        status = solver.Solve(model)
        
        # Step 9: Extract and analyze results
        return self._extract_results(
            status, solver, projects, people, project_vars, assignment_vars
        )
    
    # ==================== Time Window ====================
    
    def _compute_time_window(
        self, 
        projects: List[Project], 
        people: List[Person]
    ) -> TimeWindow:
        """
        Compute the time window for scheduling.
        
        Finds the earliest date across all data and the active project window.
        """
        min_date = None
        
        # Find earliest date from people
        for person in people:
            if not min_date or person.joining_date < min_date:
                min_date = person.joining_date
            for busy_range in person.schedule:
                if not min_date or busy_range.start_date < min_date:
                    min_date = busy_range.start_date
        
        # Find earliest date from projects
        project_starts = []
        project_ends = []
        for project in projects:
            for task in project.tasks:
                for r in task.required_ranges:
                    if not min_date or r.start_date < min_date:
                        min_date = r.start_date
                    project_starts.append(r.start_date)
                    project_ends.append(r.end_date)
        
        # Fallback if no dates found
        if not min_date:
            min_date = self.config.fallback_min_date
        
        # Determine active window for workload balancing
        if project_starts:
            window_start_date = min(project_starts)
            window_end_date = max(project_ends)
            window_start = (window_start_date - min_date).days
            window_end = (window_end_date - min_date).days
        else:
            window_start = 0
            window_end = 365
        
        return TimeWindow(
            min_date=min_date,
            start_day=window_start,
            end_day=window_end
        )
    
    # ==================== Skill Maps ====================
    
    def _build_skill_maps(self, people: List[Person]) -> Dict[str, PersonSkillMap]:
        """Build efficient skill lookup maps for each person."""
        skill_maps = {}
        for person in people:
            skill_to_eff = {}
            skill_to_pref = {}
            for skill in person.skills:
                skill_to_eff[skill.id] = getattr(skill, 'efficiency', 1)
                skill_to_pref[skill.id] = getattr(skill, 'preference_score', 1)
            skill_maps[person.id] = PersonSkillMap(
                skill_to_efficiency=skill_to_eff,
                skill_to_preference=skill_to_pref
            )
        return skill_maps
    
    # ==================== Variables ====================
    
    def _create_project_variables(
        self, 
        model: cp_model.CpModel, 
        projects: List[Project]
    ) -> Dict[str, cp_model.IntVar]:
        """Create boolean variables for each project (scheduled or not)."""
        project_vars = {}
        for project in projects:
            project_vars[project.id] = model.NewBoolVar(f'project_{project.id}')
        return project_vars
    
    def _create_assignment_variables(
        self,
        model: cp_model.CpModel,
        projects: List[Project],
        people: List[Person],
        skill_maps: Dict[str, PersonSkillMap],
        time_window: TimeWindow
    ) -> Tuple[Dict[Tuple[str, str], cp_model.IntVar], Dict[str, List[AssignmentCandidate]]]:
        """
        Create assignment variables for valid person-task pairs.
        
        Returns:
            - assignment_vars: Dict[(task_id, person_id)] -> BoolVar
            - person_assignments: Dict[person_id] -> List[AssignmentCandidate]
        """
        assignment_vars = {}
        person_assignments = {person.id: [] for person in people}
        
        for project in projects:
            for task in project.tasks:
                # Precompute task geometry
                geometry = self._compute_task_geometry(task, time_window)
                
                for person in people:
                    # Check if person has required skill
                    if not skill_maps[person.id].has_skill(task.skill_id):
                        continue
                    
                    # Check employment validity
                    if not self._is_employment_valid(person, task):
                        continue
                    
                    # Create assignment variable
                    var = model.NewBoolVar(f't{task.id}_p{person.id}')
                    assignment_vars[(task.id, person.id)] = var
                    
                    # Track for person-centric constraints
                    person_assignments[person.id].append(
                        AssignmentCandidate(task=task, var=var, geometry=geometry)
                    )
        
        return assignment_vars, person_assignments
    
    def _compute_task_geometry(
        self, 
        task: Task, 
        time_window: TimeWindow
    ) -> TaskGeometry:
        """Precompute task time ranges and total load."""
        ranges = []
        total_load = 0
        
        for r in task.required_ranges:
            start_idx = time_window.date_to_index(r.start_date)
            end_idx = time_window.date_to_index(r.end_date) + 1  # Exclusive
            ranges.append((start_idx, end_idx))
            total_load += time_window.get_overlap_days(start_idx, end_idx)
        
        return TaskGeometry(ranges=ranges, total_load=total_load)
    
    def _is_employment_valid(self, person: Person, task: Task) -> bool:
        """Check if person is employed during all task ranges."""
        for r in task.required_ranges:
            if r.start_date < person.joining_date:
                return False
            if person.termination_date and r.end_date > person.termination_date:
                return False
        return True
    
    # ==================== Constraints ====================
    
    def _add_fulfillment_constraints(
        self,
        model: cp_model.CpModel,
        projects: List[Project],
        people: List[Person],
        project_vars: Dict[str, cp_model.IntVar],
        assignment_vars: Dict[Tuple[str, str], cp_model.IntVar],
        skill_maps: Dict[str, PersonSkillMap]
    ):
        """
        Add constraints ensuring tasks are fulfilled if project is scheduled.
        
        For each task in a scheduled project:
        - Sum of (assignment * efficiency) >= workforce_count
        - If project is not scheduled, no assignments
        """
        for project in projects:
            p_var = project_vars[project.id]
            
            for task in project.tasks:
                relevant_vars = []
                efficiencies = []
                
                for person in people:
                    if (task.id, person.id) in assignment_vars:
                        var = assignment_vars[(task.id, person.id)]
                        eff = skill_maps[person.id].get_efficiency(task.skill_id)
                        relevant_vars.append(var)
                        efficiencies.append(eff)
                
                # If no one can do this task, project cannot be scheduled
                if not relevant_vars:
                    if task.workforce_count > 0:
                        model.Add(p_var == 0)
                    continue
                
                # If project is scheduled, task must be fulfilled
                model.Add(
                    sum(v * e for v, e in zip(relevant_vars, efficiencies)) >= task.workforce_count
                ).OnlyEnforceIf(p_var)
                
                # If project is not scheduled, no assignments
                for var in relevant_vars:
                    model.Add(var == 0).OnlyEnforceIf(p_var.Not())
    
    def _add_interval_constraints(
        self,
        model: cp_model.CpModel,
        people: List[Person],
        person_assignments: Dict[str, List[AssignmentCandidate]],
        skill_maps: Dict[str, PersonSkillMap],
        time_window: TimeWindow,
        projects: List[Project]
    ) -> List[cp_model.IntVar]:
        """
        Add interval constraints for each person to prevent conflicts.
        
        Returns:
            List of workload squared variables for objective function
        """
        # Track which tasks are in projects being scheduled
        project_task_ids = self._get_project_task_ids(projects)
        
        workload_sq_vars = []
        
        for person in people:
            # Build interval data for this person
            intervals_data = []
            
            # 1. Add busy schedule intervals (fixed)
            busy_intervals, busy_load = self._add_busy_intervals(
                model, person, time_window
            )
            intervals_data.extend(busy_intervals)
            
            # 2. Add locked task intervals (fixed assignments not in current projects)
            locked_intervals, locked_load = self._add_locked_task_intervals(
                model, person, project_task_ids, time_window
            )
            intervals_data.extend(locked_intervals)
            
            # 3. Add new assignment intervals (optional, controlled by variables)
            new_intervals, new_load_expr = self._add_assignment_intervals(
                model, person, person_assignments[person.id], busy_intervals
            )
            intervals_data.extend(new_intervals)
            
            # 4. Add efficiency and conflict constraints
            self._add_person_interval_constraints(
                model, person, intervals_data, skill_maps[person.id]
            )
            
            # 5. Track workload for balancing
            workload_sq_var = self._add_workload_tracking(
                model, person, busy_load, locked_load, new_load_expr
            )
            workload_sq_vars.append(workload_sq_var)
        
        return workload_sq_vars
    
    def _get_project_task_ids(self, projects: List[Project]) -> Set[str]:
        """Get set of all task IDs in the projects being scheduled."""
        task_ids = set()
        for project in projects:
            for task in project.tasks:
                task_ids.add(task.id)
        return task_ids
    
    def _add_busy_intervals(
        self,
        model: cp_model.CpModel,
        person: Person,
        time_window: TimeWindow
    ) -> Tuple[List[Tuple], int]:
        """
        Add busy schedule intervals for a person.
        
        Returns:
            - List of (interval_var, skill_id, start, end, control_var)
            - Total busy load
        """
        intervals = []
        total_load = 0
        
        for busy_range in person.schedule:
            start = time_window.date_to_index(busy_range.start_date)
            dur = (busy_range.end_date - busy_range.start_date).days + 1
            end = start + dur
            
            interval_var = model.NewIntervalVar(
                start, dur, end, f'busy_p{person.id}_{start}'
            )
            
            # Busy intervals block all skills (use None as skill_id marker)
            intervals.append((interval_var, None, start, end, None))
            total_load += time_window.get_overlap_days(start, end)
        
        return intervals, total_load
    
    def _add_locked_task_intervals(
        self,
        model: cp_model.CpModel,
        person: Person,
        project_task_ids: Set[str],
        time_window: TimeWindow
    ) -> Tuple[List[Tuple], int]:
        """
        Add intervals for locked (pre-assigned) tasks not in current projects.
        
        Returns:
            - List of (interval_var, skill_id, start, end, control_var)
            - Total locked load
        """
        intervals = []
        total_load = 0
        
        for task in person.assigned_tasks:
            # Skip tasks that are in the projects being scheduled
            if task.id in project_task_ids:
                continue
            
            skill_id = task.skill_id
            
            for r in task.required_ranges:
                start = time_window.date_to_index(r.start_date)
                dur = (r.end_date - r.start_date).days + 1
                end = start + dur
                
                interval_var = model.NewIntervalVar(
                    start, dur, end, f'locked_t{task.id}_p{person.id}'
                )
                
                # Fixed interval (control_var = None means always active)
                intervals.append((interval_var, skill_id, start, end, None))
                total_load += time_window.get_overlap_days(start, end)
        
        return intervals, total_load
    
    def _add_assignment_intervals(
        self,
        model: cp_model.CpModel,
        person: Person,
        candidates: List[AssignmentCandidate],
        busy_intervals: List[Tuple]
    ) -> Tuple[List[Tuple], List]:
        """
        Add optional intervals for new task assignments.
        
        Returns:
            - List of (interval_var, skill_id, start, end, control_var)
            - List of load expressions for workload tracking
        """
        intervals = []
        load_expressions = []
        
        for candidate in candidates:
            task = candidate.task
            var = candidate.var
            geometry = candidate.geometry
            
            # Check if blocked by busy schedule
            if self._is_blocked_by_busy(geometry.ranges, busy_intervals):
                model.Add(var == 0)
                continue
            
            # Add to load tracking
            if geometry.total_load > 0:
                load_expressions.append(var * geometry.total_load)
            
            # Create optional intervals for each time range
            for i, (start, end) in enumerate(geometry.ranges):
                dur = end - start
                opt_interval = model.NewOptionalIntervalVar(
                    start, dur, end, var, f'opt_t{task.id}_p{person.id}_{i}'
                )
                intervals.append((opt_interval, task.skill_id, start, end, var))
        
        return intervals, load_expressions
    
    def _is_blocked_by_busy(
        self, 
        task_ranges: List[Tuple[int, int]], 
        busy_intervals: List[Tuple]
    ) -> bool:
        """Check if task ranges overlap with any busy intervals."""
        for _, _, b_start, b_end, _ in busy_intervals:
            for start, end in task_ranges:
                if max(start, b_start) < min(end, b_end):
                    return True
        return False
    
    def _add_person_interval_constraints(
        self,
        model: cp_model.CpModel,
        person: Person,
        intervals_data: List[Tuple],
        skill_map: PersonSkillMap
    ):
        """
        Add constraints to prevent conflicts.
        
        Enforces strict 'One Person, One Task' policy:
        - No two intervals can overlap (regardless of skill).
        - Efficiency is treated as 'Rate of Work', not 'Concurrency Capacity'.
        - Existing data conflicts (Fixed vs Fixed) are ignored to be robust.
        """
        # Iterate all pairs to enforce non-overlap
        for i in range(len(intervals_data)):
            for j in range(i + 1, len(intervals_data)):
                self._add_single_exclusion(model, intervals_data[i], intervals_data[j])

    def _add_single_exclusion(
        self,
        model: cp_model.CpModel,
        data1: Tuple,
        data2: Tuple
    ):
        """Add exclusion constraint between two intervals if they overlap."""
        _, _, st1, en1, c1 = data1
        _, _, st2, en2, c2 = data2
        
        # Check if intervals overlap
        if max(st1, st2) < min(en1, en2):
            # They overlap - add exclusion constraint
            if c1 is None and c2 is None:
                # Both fixed - this is a data conflict, allow it
                # (existing assignments should be respected)
                pass
            elif c1 is None:
                # c1 fixed, c2 variable -> c2 must be 0
                model.Add(c2 == 0)
            elif c2 is None:
                # c2 fixed, c1 variable -> c1 must be 0
                model.Add(c1 == 0)
            else:
                # Both variable -> at most one can be active
                model.Add(c1 + c2 <= 1)
    
    def _add_workload_tracking(
        self,
        model: cp_model.CpModel,
        person: Person,
        busy_load: int,
        locked_load: int,
        new_load_expr: List
    ) -> cp_model.IntVar:
        """
        Track total workload and create squared variable for balancing.
        
        Returns:
            Workload squared variable
        """
        base_load = busy_load + locked_load
        
        # Total workload
        workload_var = model.NewIntVar(0, 100000, f'workload_{person.id}')
        model.Add(workload_var == base_load + sum(new_load_expr))
        
        # Squared workload for variance minimization
        workload_sq_var = model.NewIntVar(0, 100000**2, f'sq_workload_{person.id}')
        model.AddMultiplicationEquality(workload_sq_var, [workload_var, workload_var])
        
        return workload_sq_var
    
    # ==================== Objective ====================
    
    def _define_objective(
        self,
        model: cp_model.CpModel,
        project_vars: Dict[str, cp_model.IntVar],
        assignment_vars: Dict[Tuple[str, str], cp_model.IntVar],
        workload_sq_vars: List[cp_model.IntVar],
        projects: List[Project],
        skill_maps: Dict[str, PersonSkillMap]
    ):
        """
        Define the optimization objective function.
        
        Maximize:
            1. Number of completed projects (highest priority)
            2. Minimize number of assignments (prefer efficiency)
            3. Maximize preference score (preference_weight)
            4. Minimize workload variance (balance load)
        """
        total_projects = sum(project_vars.values())
        total_assignments = sum(assignment_vars.values())
        total_sq_workload = sum(workload_sq_vars)

        # Calculate total preference score
        total_preference = 0
        
        # Iterate over all potential assignments
        # assignment_vars keys are (task_id, person_id)
        # We need to map task_id back to skill_id to look up preference
        
        # Build task_id -> skill_id map
        task_skill_map = {}
        for project in projects:
            for task in project.tasks:
                task_skill_map[task.id] = task.skill_id
        
        for (task_id, person_id), var in assignment_vars.items():
            skill_id = task_skill_map.get(task_id)
            if skill_id:
                preference = skill_maps[person_id].get_preference(skill_id)
                total_preference += var * preference
        
        model.Maximize(
            total_projects * self.config.project_weight
            - total_assignments * self.config.assignment_cost
            + total_preference * self.config.preference_weight
            - total_sq_workload * self.config.workload_cost
        )
    
    # ==================== Solver ====================
    
    def _create_solver(self) -> cp_model.CpSolver:
        """Create and configure the CP-SAT solver."""
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = self.config.num_workers
        solver.parameters.max_time_in_seconds = self.config.max_time_seconds
        return solver
    
    # ==================== Results ====================
    
    def _extract_results(
        self,
        status: int,
        solver: cp_model.CpSolver,
        projects: List[Project],
        people: List[Person],
        project_vars: Dict[str, cp_model.IntVar],
        assignment_vars: Dict[Tuple[str, str], cp_model.IntVar]
    ) -> Tuple[List[ProjectAnalysisResult], List[ProjectAnalysisResult]]:
        """Extract and analyze results from the solved model."""
        feasible_results = []
        infeasible_results = []
        
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Solver failed
            for project in projects:
                result = self._build_result(
                    project, False, "Solver failed to find solution", {}
                )
                infeasible_results.append(result)
            return feasible_results, infeasible_results
        
        # Apply assignments for feasible projects
        for project in projects:
            p_var = project_vars[project.id]
            is_active = (solver.Value(p_var) == 1)
            
            # Reset assignees
            for task in project.tasks:
                task.assignees = []
            
            if is_active:
                # Apply assignments
                for task in project.tasks:
                    for person in people:
                        if (task.id, person.id) in assignment_vars:
                            var = assignment_vars[(task.id, person.id)]
                            if solver.Value(var) == 1:
                                task.assignees.append(person)
                                if task not in person.assigned_tasks:
                                    person.assigned_tasks.append(task)
                
                result = self._build_result(project, True, None, {})
                feasible_results.append(result)
            else:
                # Analyze why project failed
                reason, task_errors = self._analyze_failure_reason(project, people)
                result = self._build_result(project, False, reason, task_errors)
                infeasible_results.append(result)
        
        return feasible_results, infeasible_results
    
    # ==================== Failure Analysis ====================
    
    def _analyze_failure_reason(
        self, 
        project: Project, 
        people: List[Person]
    ) -> Tuple[str, Dict[str, str]]:
        """
        Analyze why a project could not be scheduled.
        
        Returns:
            - Overall failure reason
            - Dict of task_id -> specific failure message
        """
        task_failures = {}
        project_reasons = []
        
        for task in project.tasks:
            # 1. Check if anyone has the required skill
            skilled_people = [
                p for p in people 
                if any(s.id == task.skill_id for s in p.skills)
            ]
            
            if not skilled_people:
                msg = f"No workforce found with skill: {task.required_skill.name}"
                task_failures[task.id] = msg
                project_reasons.append(msg)
                continue
            
            # 2. Check employment validity
            employed_people = [
                p for p in skilled_people 
                if self._is_employment_valid(p, task)
            ]
            
            if not employed_people:
                msg = "No skilled workforce employed during task dates"
                task_failures[task.id] = msg
                project_reasons.append(msg)
                continue
            
            # 3. Check available capacity
            total_efficiency = self._calculate_available_efficiency(
                task, employed_people
            )
            
            if total_efficiency < task.workforce_count:
                # IMPORTANT: Detailed Analysis
                details = self._explain_unavailability(task, employed_people)
                
                msg = f"Insufficient capacity. Required: {task.workforce_count}, Available: {total_efficiency}. {details}"
                task_failures[task.id] = msg
                project_reasons.append(f"Task '{task.name}': {msg}")
        
        if not project_reasons:
            return "Conflict with other assignments or internal project overlap", task_failures
        
        return "; ".join(project_reasons[:3]), task_failures

    def _explain_unavailability(self, task: Task, people: List[Person]) -> str:
        """
        Generate a detailed explanation of why skilled people are unavailable.
        """
        reasons = []
        
        for person in people:
            # Check availability again to find the blocker
            blocked_by = []
            
            is_busy = False
            for task_range in task.required_ranges:
                # Check busy schedule
                for busy_range in person.schedule:
                    if self._ranges_overlap(task_range, busy_range):
                        range_str = f"{busy_range.start_date} to {busy_range.end_date}"
                        blocked_by.append(f"Busy: {range_str}")
                        is_busy = True
                        break
                if is_busy: break
                
                # Check assigned tasks
                for assigned_task in person.assigned_tasks:
                    for assigned_range in assigned_task.required_ranges:
                        if self._ranges_overlap(task_range, assigned_range):
                            blocked_by.append(f"Assigned to {assigned_task.name}")
                            is_busy = True
                            break
                    if is_busy: break
                if is_busy: break
            
            if blocked_by:
                reasons.append(f"{person.name} ({', '.join(blocked_by)})")
        
        if not reasons:
            return "All skilled people are fully booked."
            
        return "Blocked: " + ", ".join(reasons)
    
    def _calculate_available_efficiency(
        self, 
        task: Task, 
        people: List[Person]
    ) -> int:
        """
        Calculate total available efficiency for a task.
        
        Considers existing assignments and busy schedules.
        """
        total_efficiency = 0
        
        for person in people:
            # Get person's efficiency for this skill
            efficiency = next(
                (s.efficiency for s in person.skills if s.id == task.skill_id), 
                1
            )
            
            # Check if person is available for all task ranges
            is_available = True
            for task_range in task.required_ranges:
                # Check busy schedule
                for busy_range in person.schedule:
                    if self._ranges_overlap(task_range, busy_range):
                        is_available = False
                        break
                
                if not is_available:
                    break
                
                # Check assigned tasks
                for assigned_task in person.assigned_tasks:
                    for assigned_range in assigned_task.required_ranges:
                        if self._ranges_overlap(task_range, assigned_range):
                            is_available = False
                            break
                    if not is_available:
                        break
                
                if not is_available:
                    break
            
            if is_available:
                total_efficiency += efficiency
        
        return total_efficiency
    
    def _ranges_overlap(self, range1: DateRange, range2: DateRange) -> bool:
        """Check if two date ranges overlap."""
        return not (range1.end_date < range2.start_date or range1.start_date > range2.end_date)
    
    # ==================== Result Building ====================
    
    def _build_result(
        self, 
        project: Project, 
        feasible: bool, 
        failure_reason: Optional[str], 
        task_failures: Dict[str, str]
    ) -> ProjectAnalysisResult:
        """Build a ProjectAnalysisResult from project data."""
        tasks_analyzed = []
        
        for task in project.tasks:
            # Convert required ranges
            req_ranges = [
                DateRange(start_date=r.start_date, end_date=r.end_date) 
                for r in task.required_ranges
            ]
            
            # Convert assignees
            assignees_read = []
            for person in task.assignees:
                assignees_read.append(PersonRead(
                    id=person.id,
                    name=person.name,
                    joining_date=person.joining_date,
                    termination_date=person.termination_date,
                    skills=[
                        SkillRead(
                            id=s.id, 
                            name=s.name, 
                            efficiency=s.efficiency,
                            preference_score=getattr(s, 'preference_score', 1)
                        ) 
                        for s in person.skills
                    ],
                    busy_ranges=[
                        DateRange(start_date=b.start_date, end_date=b.end_date) 
                        for b in person.schedule
                    ]
                ))
            
            tasks_analyzed.append(TaskAnalysisResult(
                id=task.id,
                name=task.name,
                project_id=project.id,
                skill_id=task.skill_id,
                assignees=assignees_read,
                required_skill=SkillRead(
                    id=task.required_skill.id, 
                    name=task.required_skill.name
                ),
                required_ranges=req_ranges,
                workforce_count=task.workforce_count,
                failure_reason=task_failures.get(task.id)
            ))
        
        return ProjectAnalysisResult(
            id=project.id,
            name=project.name,
            tasks=tasks_analyzed,
            feasible=feasible,
            failure_reason=failure_reason
        )
    
    # ==================== Legacy Methods ====================
    
    def schedule_project(self, project: Project, people: List[Person]):
        """
        Legacy method - use schedule_all instead.
        
        Raises:
            NotImplementedError: This method is deprecated
        """
        raise NotImplementedError("Use schedule_all with optimization")
