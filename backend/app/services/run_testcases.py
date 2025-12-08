import yaml
import os
from datetime import date, datetime
from typing import List, Dict

from backend.app.services.models import (
    Project, Person, Task, Skill, PersonSkill, TaskRequiredRange, PersonBusyRange
)
from backend.app.services.scheduler import SchedulerService

def parse_date(d_str: str) -> date:
    return datetime.strptime(d_str, "%Y-%m-%d").date()

def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, str_presenter)

def run_testcase(filepath: str):
    print(f"\n--- Running Test Case: {os.path.basename(filepath)} ---")
    
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)
        
    # Helpers for IDs
    skill_map: Dict[str, Skill] = {}
    skill_counter = 1
    
    def get_skill(name: str) -> Skill:
        nonlocal skill_counter
        if name not in skill_map:
            skill_map[name] = Skill(id=skill_counter, name=name)
            skill_counter += 1
        return skill_map[name]

    # Parse People
    people = []
    for i, p_data in enumerate(data.get('people', [])):
        pid = i + 1
        p_skills = []
        for s_entry in p_data.get('skills', []):
            if isinstance(s_entry, str):
                # Legacy format
                s_base = get_skill(s_entry)
                p_skills.append(PersonSkill(id=s_base.id, name=s_base.name, efficiency=1))
            else:
                s_name = s_entry['name']
                eff = s_entry.get('efficiency', 1)
                s_base = get_skill(s_name)
                p_skills.append(PersonSkill(id=s_base.id, name=s_base.name, efficiency=eff))
        # Assume no explicit busy ranges in this simple format unless added
        schedule = [] 
        if 'busy' in p_data:
            for b in p_data['busy']:
                schedule.append(PersonBusyRange(
                    start_date=parse_date(b[0]), 
                    end_date=parse_date(b[1]),
                    person_id=pid
                ))
        
        person = Person(
            id=pid,
            name=p_data['name'],
            joining_date=date(2020, 1, 1), # Default
            termination_date=None,
            skills=p_skills,
            schedule=schedule,
            assigned_tasks=[]
        )
        people.append(person)
        
    # Parse Projects
    projects = []
    task_counter = 1
    project_counter = 1
    
    for proj_data in data.get('projects', []):
        proj_id = project_counter
        project_counter += 1
        
        tasks = []
        for t_data in proj_data.get('tasks', []):
            tid = task_counter
            task_counter += 1
            
            t_skill = get_skill(t_data['skill'])
            ranges = []
            for r in t_data.get('ranges', []):
                ranges.append(TaskRequiredRange(
                    start_date=parse_date(r[0]),
                    end_date=parse_date(r[1]),
                    task_id=tid
                ))
            
            task = Task(
                id=tid,
                name=t_data['name'],
                project_id=proj_id,
                skill_id=t_skill.id,
                workforce_count=t_data.get('workforce_count', 1),
                required_skill=t_skill,
                required_ranges=ranges,
                assignees=[]
            )
            tasks.append(task)
            
        project = Project(
            id=proj_id,
            name=proj_data['name'],
            tasks=tasks
        )
        projects.append(project)

    # Run Scheduler
    scheduler = SchedulerService()
    feasible, infeasible = scheduler.schedule_all(projects, people)
    
    print(f"Feasible Projects: {len(feasible)}")
    for p in feasible:
        print(f"  [OK] {p.name}")
        for t in p.tasks:
            assignees = [a.name for a in t.assignees]
            print(f"    - {t.name}: {', '.join(assignees)}")
            
    print(f"Infeasible Projects: {len(infeasible)}")
    for p in infeasible:
        print(f"  [FAIL] {p.name}: {p.failure_reason}")
        for t in p.tasks:
            if t.failure_reason:
                print(f"    - {t.name}: {t.failure_reason}")


def main():
    test_dir = "/Users/princesharma74/Documents/Workforce Allotment/backend/app/services/testcases"
    files = sorted([f for f in os.listdir(test_dir) if f.endswith('.yaml')])
    
    for f in files:
        run_testcase(os.path.join(test_dir, f))

if __name__ == "__main__":
    main()
