import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000/api/v1"

def get_people():
    try:
        resp = requests.get(f"{API_URL}/people/")
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"API Error: {e}")
    return []

def get_skills():
    try:
        resp = requests.get(f"{API_URL}/skills/")
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"API Error: {e}")
    return []

def create_skill(name):
    return requests.post(f"{API_URL}/skills/", json={"name": name})

def create_person(payload):
    return requests.post(f"{API_URL}/people/", json=payload)

def get_projects():
    try:
        resp = requests.get(f"{API_URL}/projects/")
        if resp.status_code == 200:
            return resp.json()
    except:
        return []
    return []

def create_project(payload):
    return requests.post(f"{API_URL}/projects/", json=payload)

def assign_task(task_id, person_id):
    return requests.put(f"{API_URL}/projects/tasks/{task_id}/assign?person_id={person_id}")

def unassign_task(task_id, person_id):
    return requests.delete(f"{API_URL}/projects/tasks/{task_id}/assign?person_id={person_id}")

def bulk_assign_tasks(assignments_list):
    # assignments_list: list of dicts {'task_id': int, 'person_id': int}
    return requests.post(f"{API_URL}/projects/assignments/bulk", json={"assignments": assignments_list})

def run_scheduler(dry_run=False):
    return requests.post(f"{API_URL}/scheduler/run", params={"dry_run": dry_run})

def delete_skill(skill_id):
    return requests.delete(f"{API_URL}/skills/{skill_id}")

def update_skill(skill_id, name):
    return requests.put(f"{API_URL}/skills/{skill_id}", json={"name": name})

def delete_person(person_id):
    return requests.delete(f"{API_URL}/people/{person_id}")

def update_person(person_id, payload):
    return requests.put(f"{API_URL}/people/{person_id}", json=payload)

def delete_project(project_id):
    return requests.delete(f"{API_URL}/projects/{project_id}")

def update_project(project_id, payload):
    return requests.put(f"{API_URL}/projects/{project_id}", json=payload)

def delete_task(task_id):
    return requests.delete(f"{API_URL}/projects/tasks/{task_id}")

def update_task(task_id, payload):
    return requests.put(f"{API_URL}/projects/tasks/{task_id}", json=payload)
