from typing import List, Tuple, Dict, Optional
from datetime import timedelta
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
                busy_int = model.NewFixedIntervalVar(start, dur, f'busy_p{person.id}_{start}')
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
                        locked_int = model.NewFixedIntervalVar(start, dur, f'locked_t{t.id}_p{person.id}')
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
        model.Maximize(sum(project_vars.values()))
        
        # --- Solve ---
        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        
        feasible_results = []
        infeasible_results = []
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for project in projects:
                p_var = project_vars[project.id]
                is_active = (solver.Value(p_var) == 1)
                
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
                else:
                    result = self._build_result(project, False, "Optimization could not accommodate this project.", {})
                    infeasible_results.append(result)
            
        else:
            for project in projects:
                infeasible_results.append(self._build_result(project, False, "Solver failed to find solution", {}))
                
        return feasible_results, infeasible_results


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

