from typing import List, Tuple, Dict, Optional
from datetime import timedelta, date
from ortools.sat.python import cp_model
from .models import (
    Project, Person, Task, 
    ProjectAnalysisResult, TaskAnalysisResult, DateRange, PersonRead, SkillRead
)

class SchedulerService:
    def schedule_all(self, projects: List[Project], people: List[Person]) -> Tuple[List[ProjectAnalysisResult], List[ProjectAnalysisResult]]:
        model = cp_model.CpModel()
        
        # --- Time Horizon ---
        # Find min date to use as epoch 0
        min_date = None
        for p in people:
            if not min_date or p.joining_date < min_date:
                min_date = p.joining_date
            for b in p.schedule:
                if not min_date or b.start_date < min_date:
                    min_date = b.start_date
        
        for p in projects:
            for t in p.tasks:
                for r in t.required_ranges:
                    if not min_date or r.start_date < min_date:
                        min_date = r.start_date

        if not min_date:
            min_date = date(2020, 1, 1) # Fallback

        def d2i(d):
            return (d - min_date).days

        # --- Variables ---
        project_vars = {}
        for p in projects:
            project_vars[p.id] = model.NewBoolVar(f'project_{p.id}')
            
        task_assignment_vars = {} # (task_id, person_id) -> BoolVar
        
        # Precompute efficiency
        person_skills_map = {}
        for person in people:
            s_map = {}
            for s in person.skills:
                s_map[s.id] = getattr(s, 'efficiency', 1)
            person_skills_map[person.id] = s_map

        # Create Assignment Variables
        for project in projects:
            for task in project.tasks:
                for person in people:
                    if task.skill_id in person_skills_map[person.id]:
                        var = model.NewBoolVar(f't{task.id}_p{person.id}')
                        task_assignment_vars[(task.id, person.id)] = var

        # --- Constraints 1: Fulfillment ---
        for project in projects:
            p_var = project_vars[project.id]
            for task in project.tasks:
                relevant_assignments = []
                efficiencies = []
                
                for person in people:
                    if (task.id, person.id) in task_assignment_vars:
                        var = task_assignment_vars[(task.id, person.id)]
                        eff = person_skills_map[person.id][task.skill_id]
                        relevant_assignments.append(var)
                        efficiencies.append(eff)
                
                if not relevant_assignments:
                    if task.workforce_count > 0:
                        model.Add(p_var == 0)
                    continue

                model.Add(sum(v * e for v, e in zip(relevant_assignments, efficiencies)) >= task.workforce_count).OnlyEnforceIf(p_var)
                
                for var in relevant_assignments:
                    model.Add(var == 0).OnlyEnforceIf(p_var.Not())

        # --- Constraints 2: Intervals & Consistency ---
        
        # Identify "Locked" tasks (currently assigned but not in the project list being rescheduled)
        project_task_ids = set()
        for p in projects:
            for t in p.tasks:
                project_task_ids.add(t.id)

        for person in people:
            # We collect all intervals for this person, tagged by Skill ID
            # Struct: (IntervalVar, SkillID)
            person_intervals = []
            
            # 1. Fixed "busy" schedule
            # Treat as "Blocking" - i.e. consumes ALL capacity?
            # Or just prevents assignment. 
            # Original logic: "Busy in manual schedule" -> Return False (Absolute block)
            # So we can create a Fixed Interval with capacity = infinity (or max efficiency) ??
            # Or just enforce that NO assigned task can overlap with Busy.
            
            busy_intervals = []
            for b in person.schedule:
                start = d2i(b.start_date)
                dur = (b.end_date - b.start_date).days + 1
                # Create a fixed interval
                # We can't use AddNoOverlap directly if we use Cumulative...
                # Actually, simpler: "Busy" consumes ALL efficiency for ALL skills.
                # Just add it to every skill's cumulative constraint? Or use NoOverlap?
                # Best: AddNoOverlap(busy, task_interval) for every task.
                
                # We'll create the IntervalVar first
                busy_int = model.NewIntervalVar(start, dur, start + dur, f'busy_p{person.id}_{start}')
                busy_intervals.append(busy_int)

            # 2. Locked Tasks (Existing Assignments)
            for t in person.assigned_tasks:
                if t.id not in project_task_ids:
                    # This task is locked.
                    s_id = t.skill_id
                    for r in t.required_ranges:
                        start = d2i(r.start_date)
                        dur = (r.end_date - r.start_date).days + 1
                        # It is present
                        locked_int = model.NewIntervalVar(start, dur, start + dur, f'locked_t{t.id}_p{person.id}')
                        person_intervals.append((locked_int, s_id))
            
            # 3. New Potential Assignments
            for project in projects:
                for task in project.tasks:
                    if (task.id, person.id) in task_assignment_vars:
                        var = task_assignment_vars[(task.id, person.id)]
                        s_id = task.skill_id
                        
                        # Employment check (Hard constraint)
                        # employment enforcement
                        valid_employment = True
                        for r in task.required_ranges:
                            if r.start_date < person.joining_date: 
                                valid_employment = False
                            if person.termination_date and r.end_date > person.termination_date:
                                valid_employment = False
                        
                        if not valid_employment:
                            model.Add(var == 0)
                            continue

                        # Create Optional Intervals
                        for i, r in enumerate(task.required_ranges):
                            start = d2i(r.start_date)
                            dur = (r.end_date - r.start_date).days + 1
                            opt_int = model.NewOptionalIntervalVar(start, dur, start + dur, var, f'opt_t{task.id}_p{person.id}_{i}')
                            
                            person_intervals.append((opt_int, s_id))
                            
                            # Enforce Busy Overlap Check immediately
                            for b_int in busy_intervals:
                                model.AddNoOverlap([opt_int, b_int])

            # --- Enforce Efficiency & conflicts per person ---
            
            # Group by Skill
            by_skill = {}
            for iv, s_id in person_intervals:
                if s_id not in by_skill:
                    by_skill[s_id] = []
                by_skill[s_id].append(iv)
                
            # A. Same Skill: Cumulative Constraint
            for s_id, intervals in by_skill.items():
                eff = person_skills_map[person.id].get(s_id, 1)
                # Ensure sum of active tasks <= efficiency
                # Demands are all 1
                if intervals:
                    model.AddCumulative(intervals, [1]*len(intervals), eff)
                    
            # B. Different Skills: No Overlap
            # Pairwise check between intervals of different skills
            skill_ids = list(by_skill.keys())
            for i in range(len(skill_ids)):
                for j in range(i + 1, len(skill_ids)):
                    s1 = skill_ids[i]
                    s2 = skill_ids[j]
                    
                    intervals1 = by_skill[s1]
                    intervals2 = by_skill[s2]
                    
                    for iv1 in intervals1:
                        for iv2 in intervals2:
                            model.AddNoOverlap([iv1, iv2])

        # --- Objective ---
        
        # 3. Load Balancing (Workload Distribution)
        # We want to distribute workload within the active window of the projects being scheduled.
        
        # Determine active window
        window_start = min_date # Fallback
        window_end = min_date
        
        p_starts = []
        p_ends = []
        for p in projects:
            for t in p.tasks:
                for r in t.required_ranges:
                    p_starts.append(r.start_date)
                    p_ends.append(r.end_date)
        
        if p_starts:
            window_start = min(p_starts)
            window_end = max(p_ends)
        else:
            window_end = window_start + timedelta(days=365)

        workload_sq_vars = []
        
        for person in people:
            base_load = 0
            
            # Intersection helper
            def get_overlap(r_start, r_end):
                os = max(r_start, window_start)
                oe = min(r_end, window_end)
                if oe >= os:
                    return (oe - os).days + 1
                return 0

            # 1. Busy Schedule
            for b in person.schedule:
                base_load += get_overlap(b.start_date, b.end_date)
            
            # 2. Locked Tasks
            for t in person.assigned_tasks:
                if t.id not in project_task_ids:
                    for r in t.required_ranges:
                        base_load += get_overlap(r.start_date, r.end_date)
            
            # 3. New Assignments (Variables)
            new_load_expr = []
            for project in projects:
                for task in project.tasks:
                    if (task.id, person.id) in task_assignment_vars:
                         var = task_assignment_vars[(task.id, person.id)]
                         task_load = 0
                         for r in task.required_ranges:
                             task_load += get_overlap(r.start_date, r.end_date)
                         
                         if task_load > 0:
                             new_load_expr.append(var * task_load)
            
            # Create Workload Variable
            # We assume a reasonable upper bound for workload days.
            # Safe bound: 100,000 (approx 270 years)
            w_var = model.NewIntVar(0, 100000, f'workload_{person.id}')
            model.Add(w_var == base_load + sum(new_load_expr))
            
            # Square it to penalize peaks
            w_sq_var = model.NewIntVar(0, 100000**2, f'sq_workload_{person.id}')
            model.AddMultiplicationEquality(w_sq_var, [w_var, w_var])
            workload_sq_vars.append(w_sq_var)

        # Primary: Maximize number of active projects 
        # Secondary: Minimize Assignments (Efficiency)
        # Tertiary: Balance Workload (Minimize Sum of Squares)
        
        # Weights
        PROJECT_WEIGHT = 1000000000000 # 10^12
        ASSIGNMENT_COST = 1000000      # 10^6
        WORKLOAD_COST = 1
        
        total_assignments = sum(task_assignment_vars.values())
        total_projects = sum(project_vars.values())
        total_sq_workload = sum(workload_sq_vars)
        
        model.Maximize(
            total_projects * PROJECT_WEIGHT 
            - total_assignments * ASSIGNMENT_COST 
            - total_sq_workload * WORKLOAD_COST
        )
        
        # --- Solve ---
        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        
        feasible_results = []
        infeasible_results = []
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Pass 1: Apply Feasible Assignments
            for project in projects:
                p_var = project_vars[project.id]
                is_active = (solver.Value(p_var) == 1)
                
                # Reset assignees to be safe
                for task in project.tasks:
                    task.assignees = []
                
                if is_active:
                    for task in project.tasks:
                        for person in people:
                            if (task.id, person.id) in task_assignment_vars:
                                var = task_assignment_vars[(task.id, person.id)]
                                if solver.Value(var) == 1:
                                    task.assignees.append(person)
                                    if task not in person.assigned_tasks:
                                        person.assigned_tasks.append(task)
                                        
                    result = self._build_result(project, True, None, {})
                    feasible_results.append(result)

            # Pass 2: Analyze Infeasible Projects
            for project in projects:
                p_var = project_vars[project.id]
                is_active = (solver.Value(p_var) == 1)
                
                if not is_active:
                    reason, task_errors = self._analyze_failure_reason(project, people)
                    result = self._build_result(project, False, reason, task_errors)
                    infeasible_results.append(result)
            
        else:
            for project in projects:
                infeasible_results.append(self._build_result(project, False, "Solver failed to find solution", {}))
                
        return feasible_results, infeasible_results

    def _analyze_failure_reason(self, project: Project, people: List[Person]) -> Tuple[str, Dict[int, str]]:
        task_failures = {}
        project_reasons = []

        for task in project.tasks:
            # 1. Total Skill availability check
            skilled_people = [p for p in people if any(s.id == task.skill_id for s in p.skills)]
            if not skilled_people:
                msg = f"No workforce found with skill ID {task.skill_id}"
                task_failures[task.id] = msg
                project_reasons.append(msg)
                continue

            # 2. Employment check
            employed_people = []
            for p in skilled_people:
                valid_employment = True
                for r in task.required_ranges:
                     if r.start_date < p.joining_date:
                         valid_employment = False
                     if p.termination_date and r.end_date > p.termination_date:
                         valid_employment = False
                if valid_employment:
                    employed_people.append(p)
            
            if not employed_people:
                msg = f"No skilled workforce employed during task dates"
                task_failures[task.id] = msg
                project_reasons.append(msg)
                continue

            # 3. Efficiency/Overlap check
            # Calculate max available efficiency for this task's ranges
            # considering ALREADY ASSIGNED tasks (from Pass 1 and locked) and BUSY ranges.
            
            total_efficiency = 0
            for p in employed_people:
                eff = next((s.efficiency for s in p.skills if s.id == task.skill_id), 1)
                
                # Check conflicts
                is_available = True
                for r in task.required_ranges:
                    # Check busy
                    for b in p.schedule:
                        # Overlap logic
                        if not (r.end_date < b.start_date or r.start_date > b.end_date):
                            is_available = False
                            break
                    if not is_available: break
                    
                    # Check assigned tasks
                    for at in p.assigned_tasks:
                        for ar in at.required_ranges:
                            if not (r.end_date < ar.start_date or r.start_date > ar.end_date):
                                is_available = False
                                break
                        if not is_available: break
                    if not is_available: break
                
                if is_available:
                    total_efficiency += eff
            
            if total_efficiency < task.workforce_count:
                msg = f"Insufficient capacity. Required: {task.workforce_count}, Available: {total_efficiency}"
                task_failures[task.id] = msg
                project_reasons.append(f"Task '{task.name}': {msg}")

        if not project_reasons:
            return "Conflict with other assignments or internal project overlap", task_failures
        
        return "; ".join(project_reasons[:3]), task_failures


    def _build_result(self, project: Project, feasible: bool, failure_reason: str, task_failures: Dict[int, str]) -> ProjectAnalysisResult:
        tasks_analyzed = []
        for t in project.tasks:
            req_ranges = [DateRange(start_date=r.start_date, end_date=r.end_date) for r in t.required_ranges]
            
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

    # Legacy method, might not be needed but kept if referenced elsewhere (unlikely based on usage).
    # We can remove check_assignment_viability and rollback as they are not used in CP approach.
    def schedule_project(self, project: Project, people: List[Person]):
        raise NotImplementedError("Use schedule_all with optimization")

