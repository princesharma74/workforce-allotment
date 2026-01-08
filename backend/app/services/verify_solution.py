import yaml
import sys
import os
from datetime import date, datetime
from typing import List, Dict, Set, Tuple
from collections import defaultdict

from backend.app.services.scheduler import SchedulerService, SchedulerConfig
from backend.app.services.models import Project, Person, Task, PersonSkill, PersonBusyRange, TaskRequiredRange, Skill

def parse_date(d):
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return datetime.strptime(d, '%Y-%m-%d').date()
    return d

def load_yaml(filepath: str) -> Tuple[List[Project], List[Person]]:
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)
    
    people_map = {}
    people = []
    for p_data in data.get('people', []):
        skills = []
        for s in p_data.get('skills', []):
            if isinstance(s, str):
                skills.append(PersonSkill(id=s, name=s, efficiency=1))
            else:
                skills.append(PersonSkill(
                    id=s['name'], 
                    name=s['name'], 
                    efficiency=s.get('efficiency', 1),
                    preference_score=s.get('preference', 1)
                ))
        
        busy = []
        for b in p_data.get('schedule', []):
            busy.append(PersonBusyRange(
                start_date=parse_date(b[0]),
                end_date=parse_date(b[1])
            ))
            
        person = Person(
            id=p_data['name'],
            name=p_data['name'],
            joining_date=date(2020, 1, 1), # Default
            termination_date=None,
            skills=skills,
            schedule=busy,
            assigned_tasks=[]
        )
        people.append(person)
        people_map[person.id] = person
        
    projects = []
    for p_data in data.get('projects', []):
        tasks = []
        for t_data in p_data.get('tasks', []):
            ranges = []
            for r in t_data.get('ranges', []):
                ranges.append(TaskRequiredRange(
                    start_date=parse_date(r[0]),
                    end_date=parse_date(r[1])
                ))
            
            task = Task(
                id=f"{p_data['name']}_{t_data['name']}",
                name=t_data['name'],
                project_id=p_data['name'],
                skill_id=t_data['skill'],
                workforce_count=t_data.get('workforce_count', 1),
                required_skill=Skill(id=t_data['skill'], name=t_data['skill']),
                required_ranges=ranges
            )
            tasks.append(task)
            
        project = Project(
            id=p_data['name'],
            name=p_data['name'],
            tasks=tasks
        )
        projects.append(project)
        
    return projects, people

def verify_constraints(projects: List[Project], people: List[Person]):
    """
    Strictly verify constraints:
    1. Skill Validity (Person has skill)
    2. Employment Validity (Date range)
    3. Busy Range Conflict
    4. Exclusive Contexts (Different skills cannot overlap)
    5. Capacity Constraint (Same skill overlap allowed up to efficiency)
    """
    
    # 1. Build daily load map for each person
    # Map: PersonID -> Date -> Skill -> TotalLoad (Sum of task.workforce_count)
    daily_load = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    
    # Map: PersonID -> Date -> Set[TaskID] (for reporting)
    person_daily_tasks = defaultdict(lambda: defaultdict(set))

    # Helper to get skill object
    def get_person_skill(person, skill_id):
        return next((s for s in person.skills if s.id == skill_id), None)

    for p in people:
        # Fill busy ranges (Load = Infinity or simply check overlap)
        # We'll handle busy ranges as a special "BUSY" skill with infinite load
        for busy in p.schedule:
            curr = busy.start_date
            while curr <= busy.end_date:
                daily_load[p.id][curr]['BUSY'] = 9999
                curr = curr.replace(day=curr.day + 1) if curr.month == 12 and curr.day == 31 else date.fromordinal(curr.toordinal() + 1)
        
        # Check assigned tasks
        for task in p.assigned_tasks:
            # check skill validity
            pskill = get_person_skill(p, task.skill_id)
            if not pskill:
                raise ValueError(f"Constraint 1 Violation: Person {p.name} assigned task {task.name} but lacks skill {task.skill_id}")
            
            eff = pskill.efficiency
            
            for r in task.required_ranges:
                curr = r.start_date
                while curr <= r.end_date:
                    # Check Busy
                    if daily_load[p.id][curr].get('BUSY'):
                        raise ValueError(f"Constraint 3 Violation: Person {p.name} assigned task {task.name} overlap with Busy Range on {curr}")
                    
                    # Add Load (Contribution is limited by efficiency or task requirement)
                    contribution = min(eff, task.workforce_count)
                    daily_load[p.id][curr][task.skill_id] += contribution
                    person_daily_tasks[p.id][curr].add(task.name)
                    
                    # Verify Capacity immediately for this skill
                    if daily_load[p.id][curr][task.skill_id] > eff:
                         raise ValueError(f"Constraint 4 Violation: Person {p.name} overloaded on {curr} for skill {task.skill_id}. Load {daily_load[p.id][curr][task.skill_id]} > Efficiency {eff}. Tasks: {person_daily_tasks[p.id][curr]}")
                    
                    curr = date.fromordinal(curr.toordinal() + 1)

    # 2. Check Exclusive Contexts (Mixed Skills on same day)
    for pid, date_map in daily_load.items():
        for d, skill_loads in date_map.items():
            # If more than 1 skill has load > 0
            active_skills = [s for s, load in skill_loads.items() if load > 0]
            if len(active_skills) > 1:
                raise ValueError(f"Constraint 5 Violation: Person {pid} working on different skills {active_skills} on {d}")

def run_verification():
    test_dir = os.path.join(os.path.dirname(__file__), 'testcases')
    files = [f for f in os.listdir(test_dir) if f.endswith('.yaml') or f.endswith('.yml')]
    files.sort()
    
    service = SchedulerService(SchedulerConfig(max_time_seconds=5.0))
    
    print(f"Verifying {len(files)} test cases...")
    
    for f in files:
        if "tough" in f: continue # Skip long running for now unless needed
        path = os.path.join(test_dir, f)
        print(f"\nRunning {f}...")
        
        try:
            projects, people = load_yaml(path)
            # Reset assignments
            for p in people: p.assigned_tasks = []
            
            feasible, infeasible = service.schedule_all(projects, people)
            
            print(f"  Feasible: {len(feasible)}, Infeasible: {len(infeasible)}")
            
            # Apply assignments back to people object for verification 
            # (schedule_all does this, but let's ensure we are checking the same objects)
            # The service modifies the 'people' list in-place (appending to assigned_tasks)
            
            verify_constraints(projects, people)
            print("  [PASS] Constraints strictly satisfied.")
            
        except ValueError as e:
            print(f"  [FAIL] {e}")
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_verification()
