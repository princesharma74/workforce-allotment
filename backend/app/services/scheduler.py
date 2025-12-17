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

        # Determine active window for workload balancing
        p_starts = []
        p_ends = []
        for p in projects:
            for t in p.tasks:
                for r in t.required_ranges:
                    p_starts.append(r.start_date)
                    p_ends.append(r.end_date)
        
        if p_starts:
            window_start_date = min(p_starts)
            window_end_date = max(p_ends)
            window_start = d2i(window_start_date)
            window_end = d2i(window_end_date)
        else:
            window_start = 0
            window_end = 365

        # --- Variables & Precomputation ---
        project_vars = {}
        for p in projects:
            project_vars[p.id] = model.NewBoolVar(f'project_{p.id}')
            
        task_assignment_vars = {} # (task_id, person_id) -> BoolVar
        person_potential_assignments = {} # person_id -> list of (task, var, task_load_contribution)
        
        # Precompute efficiency map
        person_skills_map = {}
        for person in people:
            s_map = {}
            for s in person.skills:
                s_map[s.id] = getattr(s, 'efficiency', 1)
            person_skills_map[person.id] = s_map
            person_potential_assignments[person.id] = []

        # Helper to calc overlap
        def get_overlap_days(start_idx, end_idx):
            s = max(start_idx, window_start)
            e = min(end_idx, window_end + 1)
            return max(0, e - s)

        # Create Assignment Variables and Pre-calculate Loads
        for project in projects:
            for task in project.tasks:
                # Precompute task geometry (ranges converted to indices)
                task_ranges_idx = []
                task_load = 0
                for r in task.required_ranges:
                    s = d2i(r.start_date)
                    e = d2i(r.end_date) + 1 # Exclusive end
                    task_ranges_idx.append((s, e))
                    task_load += get_overlap_days(s, e)
                
                # Assign vars
                for person in people:
                    if task.skill_id in person_skills_map[person.id]:
                        # Employment check (Optimization: Filter before creating var)
                        valid_employment = True
                        for r in task.required_ranges:
                            if r.start_date < person.joining_date: 
                                valid_employment = False
                            if person.termination_date and r.end_date > person.termination_date:
                                valid_employment = False
                        
                        if not valid_employment:
                            continue

                        var = model.NewBoolVar(f't{task.id}_p{person.id}')
                        task_assignment_vars[(task.id, person.id)] = var
                        
                        # Store for person-centric loops
                        person_potential_assignments[person.id].append({
                            'task': task,
                            'var': var,
                            'ranges': task_ranges_idx,
                            'load': task_load
                        })

        # --- Constraints 1: Fulfillment ---
        for project in projects:
            p_var = project_vars[project.id]
            for task in project.tasks:
                relevant_vars = []
                efficiencies = []
                
                for person in people:
                    if (task.id, person.id) in task_assignment_vars:
                        var = task_assignment_vars[(task.id, person.id)]
                        eff = person_skills_map[person.id][task.skill_id]
                        relevant_vars.append(var)
                        efficiencies.append(eff)
                
                if not relevant_vars:
                    if task.workforce_count > 0:
                        model.Add(p_var == 0)
                    continue

                model.Add(sum(v * e for v, e in zip(relevant_vars, efficiencies)) >= task.workforce_count).OnlyEnforceIf(p_var)
                
                for var in relevant_vars:
                    model.Add(var == 0).OnlyEnforceIf(p_var.Not())

        # --- Constraints 2: Intervals & Consistency ---
        
        # Identify "Locked" tasks
        project_task_ids = set()
        for p in projects:
            for t in p.tasks:
                project_task_ids.add(t.id)

        workload_sq_vars = []

        for person in people:
            # We track intervals along with their [start, end) for static overlap checking
            # List of (IntervalVar, SkillID, start_idx, end_idx)
            person_intervals_data = []
            
            # 1. Busy Schedule
            busy_intervals_data = [] # (IntervalVar, start, end)
            busy_load = 0
            for b in person.schedule:
                start = d2i(b.start_date)
                dur = (b.end_date - b.start_date).days + 1
                end = start + dur
                
                busy_int = model.NewIntervalVar(start, dur, end, f'busy_p{person.id}_{start}')
                busy_intervals_data.append((busy_int, start, end))
                busy_load += get_overlap_days(start, end)

            # 2. Locked Tasks
            locked_load = 0
            for t in person.assigned_tasks:
                if t.id not in project_task_ids:
                    s_id = t.skill_id
                    for r in t.required_ranges:
                        start = d2i(r.start_date)
                        dur = (r.end_date - r.start_date).days + 1
                        end = start + dur
                        
            # 2. Locked Tasks (from assigned_tasks)
            # These are fixed.
            locked_load = 0
            for t in person.assigned_tasks:
                if t.id not in project_task_ids:
                    s_id = t.skill_id
                    for r in t.required_ranges:
                        start = d2i(r.start_date)
                        dur = (r.end_date - r.start_date).days + 1
                        end = start + dur
                        
                        locked_int = model.NewIntervalVar(start, dur, end, f'locked_t{t.id}_p{person.id}')
                        # Fixed interval -> control_var is None (implied True/1)
                        person_intervals_data.append((locked_int, s_id, start, end, None))
                        locked_load += get_overlap_days(start, end)
            
            # 3. New Assignments
            new_load_expr = []
            possible_assignments = person_potential_assignments[person.id]
            
            for item in possible_assignments:
                task = item['task']
                var = item['var']
                ranges = item['ranges'] # List of (s, e)
                t_load = item['load']
                s_id = task.skill_id
                
                # Check Busy Conflict immediately
                is_blocked_by_busy = False
                for (b_int, b_start, b_end) in busy_intervals_data:
                    # Check overlap
                    for (start, end) in ranges:
                        if max(start, b_start) < min(end, b_end):
                            is_blocked_by_busy = True
                            break
                    if is_blocked_by_busy: break
                
                if is_blocked_by_busy:
                    model.Add(var == 0)
                    continue

                # Add to load expression
                if t_load > 0:
                    new_load_expr.append(var * t_load)
                
                for i, (start, end) in enumerate(ranges):
                    dur = end - start
                    opt_int = model.NewOptionalIntervalVar(start, dur, end, var, f'opt_t{task.id}_p{person.id}_{i}')
                    person_intervals_data.append((opt_int, s_id, start, end, var))
            
            # --- Enforce Efficiency & conflicts per person ---
            
            # Group by Skill
            by_skill = {}
            for data in person_intervals_data:
                iv, s_id, start, end, ctrl = data
                if s_id not in by_skill:
                    by_skill[s_id] = []
                by_skill[s_id].append(data)
                
            # A. Same Skill: Cumulative Constraint
            for s_id, data_list in by_skill.items():
                eff = person_skills_map[person.id].get(s_id, 1)
                intervals = [d[0] for d in data_list]
                if intervals:
                    model.AddCumulative(intervals, [1]*len(intervals), eff)
                    
            # B. Different Skills: Explicit Exclusion (Sum <= 1)
            skill_ids = list(by_skill.keys())
            for i in range(len(skill_ids)):
                for j in range(i + 1, len(skill_ids)):
                    s1 = skill_ids[i]
                    s2 = skill_ids[j]
                    
                    data1 = by_skill[s1]
                    data2 = by_skill[s2]
                    
                    for (_, _, st1, en1, c1) in data1:
                        for (_, _, st2, en2, c2) in data2:
                            # Check overlap
                            if max(st1, st2) < min(en1, en2):
                                # Conflict!
                                if c1 is None and c2 is None:
                                    # Both fixed and overlapping -> Data error or unavoidable double booking in inputs.
                                    # Ignore strict enforcement for existing data, or fail?
                                    # Existing assignments should be respected.
                                    pass
                                elif c1 is None:
                                    # c1 fixed, c2 variable -> c2 must be 0
                                    model.Add(c2 == 0)
                                elif c2 is None:
                                    # c2 fixed, c1 variable -> c1 must be 0
                                    model.Add(c1 == 0)
                                else:
                                    # Both variable
                                    model.Add(c1 + c2 <= 1)

            # --- Workload Setup ---
            base_load = busy_load + locked_load
            w_var = model.NewIntVar(0, 100000, f'workload_{person.id}')
            model.Add(w_var == base_load + sum(new_load_expr))
            
            w_sq_var = model.NewIntVar(0, 100000**2, f'sq_workload_{person.id}')
            model.AddMultiplicationEquality(w_sq_var, [w_var, w_var])
            workload_sq_vars.append(w_sq_var)

        # --- Objective ---
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
        # Optimization parameters
        solver.parameters.num_search_workers = 8 
        solver.parameters.max_time_in_seconds = 60.0 
        
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
