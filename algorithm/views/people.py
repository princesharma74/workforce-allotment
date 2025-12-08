import streamlit as st
import pandas as pd
from datetime import date, timedelta
from app.models import Person, DateRange
from app.utils import get_skill_by_name, get_person_by_name, get_project_by_name

def render_manage_people():
    st.header("Manage People")
    
    if not st.session_state.skills:
        st.error("Please add skills first.")
    else:
        tab1, tab2 = st.tabs(["Add Person", "Manual Assignment"])
        
        with tab1:
            render_add_person_tab()

        with tab2:
            render_manual_assignment_tab()

        render_roster()

def render_add_person_tab():
    # Removed st.form to allow dynamic conditional input for termination date
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Name", key="person_name_input")
        start_date = st.date_input("Available From (Joining Date)", value=date.today(), key="person_start_date")
    with c2:
        # Optional termination date
        has_term = st.checkbox("Has Termination Date?", key="person_has_term")
        term_date = st.date_input("Available Until (Termination Date)", value=date.today() + timedelta(days=365), key="person_term_date") if has_term else None

    skill_options = sorted([s.name for s in st.session_state.skills])
    selected_skills = st.multiselect("Skills", skill_options, key="person_skills")
    
    st.markdown("### Occupancies (Leaves/Busy Dates)")
    st.caption("Add existing busy schedules.")
    
    c_occ1, c_occ2, c_occ3 = st.columns([2, 2, 1])
    with c_occ1:
        occ_start = st.date_input("Busy Start", value=date.today(), key="occ_start_input")
    with c_occ2:
        occ_end = st.date_input("Busy End", value=date.today(), key="occ_end_input")
    with c_occ3:
        st.write("")
        st.write("")
        if st.button("Add Range", key="add_occ_range"):
            if occ_start <= occ_end:
                st.session_state.temp_occupancies.append(DateRange(start=occ_start, end=occ_end))
            else:
                st.error("End date must be after start date.")

    if st.session_state.temp_occupancies:
        st.write("Selected Ranges:")
        for i, r in enumerate(st.session_state.temp_occupancies):
            st.write(f"{i+1}. {r.start} to {r.end}")
        if st.button("Clear Ranges", key="clear_occ"):
            st.session_state.temp_occupancies = []
    
    st.divider()
    if st.button("Add Person", key="add_person_btn"):
        if name and selected_skills:
            person_skills = {get_skill_by_name(s_name) for s_name in selected_skills}
            
            # Copy temp occupancies
            schedule = list(st.session_state.temp_occupancies)
            
            person = Person(
                name=name, 
                skills=person_skills, 
                schedule=schedule,
                joining_date=start_date,
                termination_date=term_date
            )
            st.session_state.people.append(person)
            st.success(f"Added {name}")
            st.session_state.temp_occupancies = [] # Reset
        elif not name:
            st.error("Name is required.")
        elif not selected_skills:
            st.error("Select at least one skill.")

def render_manual_assignment_tab():
    st.subheader("Manual Task Assignment")
    if not st.session_state.people or not st.session_state.projects:
        st.info("Need both People and Projects to assign tasks.")
    else:
        # Select Person
        person_names = [p.name for p in st.session_state.people]
        selected_person_name = st.selectbox("Select Person", person_names, key="man_assign_person")
        selected_person = get_person_by_name(selected_person_name)
        
        # Select Project
        project_names = [p.name for p in st.session_state.projects]
        selected_project_name = st.selectbox("Select Project", project_names, key="man_assign_proj")
        selected_project = get_project_by_name(selected_project_name)
        
        if selected_person and selected_project:
            # Filter unassigned tasks in project that match skill? Or let user force assign?
            # User usually wants to assign valid tasks.
            available_tasks = [t for t in selected_project.tasks if t.assigned_person is None]
            if available_tasks:
                task_options = {f"{t.name} ({t.required_skill.name})": t for t in available_tasks}
                selected_task_label = st.selectbox("Select Task", list(task_options.keys()), key="man_assign_task")
                selected_task = task_options[selected_task_label]
                
                if st.button("Assign Task", key="man_assign_btn"):
                    # Check eligibility
                    if selected_task.required_skill not in selected_person.skills:
                        st.warning(f"{selected_person.name} does not have required skill: {selected_task.required_skill.name}")
                    elif not selected_person.is_available(selected_task.required_ranges):
                        st.warning(f"{selected_person.name} is not available for the required dates.")
                    else:
                        selected_person.assign_task(selected_task)
                        st.success(f"Assigned '{selected_task.name}' to {selected_person.name}")
                        st.rerun()
            else:
                st.info("No unassigned tasks in this project.")

def render_roster():
    st.subheader("Roster & Assignments")
    if st.session_state.people:
        people_data = []
        for p in st.session_state.people:
            skills_str = ", ".join([s.name for s in p.skills])
            busy_str = ", ".join([f"{r.start} to {r.end}" for r in p.schedule]) if p.schedule else "None"
            avail_str = f"{p.joining_date} -> {p.termination_date if p.termination_date else 'Indefinite'}"
            assignments_str = ", ".join([f"{t.name} ({t.project.name if t.project else 'Unknown'})" for t in p.assigned_tasks]) if p.assigned_tasks else "None"
            
            people_data.append({
                "Name": p.name, 
                "Skills": skills_str, 
                "Availability": avail_str,
                "Leaves": busy_str,
                "Assigned Tasks": assignments_str
            })
        st.table(pd.DataFrame(people_data))
    else:
        st.info("No people added yet.")
