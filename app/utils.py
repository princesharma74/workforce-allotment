import os
import yaml
import streamlit as st
from datetime import date, datetime
from typing import List, Tuple
from .models import Person, Project, Skill, DateRange, Task

def parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def load_testcases_from_directory(directory_path: str) -> List[Tuple[str, List[Person], List[Project]]]:
    scenarios = []
    if not os.path.exists(directory_path):
        print(f"Directory not found: {directory_path}")
        return []

    # Iterate over all yaml files in the directory
    files = sorted([f for f in os.listdir(directory_path) if f.endswith('.yaml') or f.endswith('.yml')])
    
    for filename in files:
        file_path = os.path.join(directory_path, filename)
        try:
            with open(file_path, 'r') as f:
                scenario_data = yaml.safe_load(f)
                
            if not scenario_data:
                continue

            name = scenario_data.get('name', filename)
            
            # Parse People
            people = []
            
            for p_data in scenario_data.get('people', []):
                p_skills = {Skill(s) for s in p_data['skills']}
                person = Person(p_data['name'], p_skills)
                
                # Handle pre-booked ranges
                if 'pre_booked' in p_data:
                    for start_str, end_str in p_data['pre_booked']:
                        person.book([DateRange(parse_date(start_str), parse_date(end_str))])
                
                people.append(person)
                
            # Parse Projects
            projects = []
            for proj_data in scenario_data.get('projects', []):
                tasks = []
                for t_data in proj_data['tasks']:
                    skill = Skill(t_data['skill'])
                    ranges = [DateRange(parse_date(r[0]), parse_date(r[1])) for r in t_data['ranges']]
                    tasks.append(Task(t_data['name'], skill, ranges))
                projects.append(Project(proj_data['name'], tasks))
                
            scenarios.append((name, people, projects))
            
        except Exception as e:
            print(f"Error parsing {filename}: {e}")

    return scenarios

def print_results(scenario_name: str, feasible: List[Project], infeasible: List[Project]):
    print(f"\n--- Scenario: {scenario_name} ---")
    print("=== Feasible Projects ===")
    if not feasible:
        print("  (None)")
    for p in feasible:
        print(f"Project: {p.name}")
        for t in p.tasks:
            assigned = t.assigned_person.name if t.assigned_person else "Unknown"
            print(f"  - Task: {t.name} -> Assigned to: {assigned}")
    
    print("\n=== Infeasible Projects ===")
    if not infeasible:
        print("  (None)")
    for p in infeasible:
        print(f"Project: {p.name}")
        print(f"  Reason: {p.failure_reason}")
        for t in p.failed_tasks:
            print(f"  - Failed Task: {t.name}, Required Skill: {t.required_skill.name}")
    print("-" * 60)

# --- Streamlit Helpers ---

def init_session_state():
    if "skills" not in st.session_state:
        st.session_state.skills = set()
    if "people" not in st.session_state:
        st.session_state.people = []
    if "projects" not in st.session_state:
        st.session_state.projects = []
    if "temp_tasks" not in st.session_state:
        st.session_state.temp_tasks = []
    if "temp_occupancies" not in st.session_state:
        st.session_state.temp_occupancies = []
    if "scheduler_results" not in st.session_state:
        st.session_state.scheduler_results = None # (feasible, infeasible, people_snapshot_with_assignments)

def get_skill_by_name(name: str):
    for s in st.session_state.skills:
        if s.name == name:
            return s
    return None

def get_person_by_name(name: str):
    for p in st.session_state.people:
        if p.name == name:
            return p
    return None

def get_project_by_name(name: str):
    for p in st.session_state.projects:
        if p.name == name:
             return p
    return None

def clear_temp_tasks():
    st.session_state.temp_tasks = []

