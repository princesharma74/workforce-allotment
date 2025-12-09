import streamlit as st
import pandas as pd
from datetime import date, timedelta
from frontend.utils.api import get_skills, create_person, get_people, get_projects, assign_task

def render_manage_people():
    st.header("Manage People")
    
    skills = get_skills()
    if not skills:
        st.error("Please add skills first.")
    else:
        tab1, tab2, tab3 = st.tabs(["Add Person", "Edit/Delete Person", "Manual Assignment"])
        
        with tab1:
            render_add_person_tab(skills)

        with tab2:
            render_edit_person_tab(skills)

        with tab3:
            render_manual_assignment_tab()

        render_roster()

def render_add_person_tab(skills):
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Name", key="person_name_input")
        email = st.text_input("Email", key="person_email_input")
        start_date = st.date_input("Available From (Joining Date)", value=date.today(), key="person_start_date")
    with c2:
        has_term = st.checkbox("Has Termination Date?", key="person_has_term")
        term_date = st.date_input("Available Until (Termination Date)", value=date.today() + timedelta(days=365), key="person_term_date") if has_term else None

    skill_options = sorted([s['name'] for s in skills])
    selected_skills = st.multiselect("Skills", skill_options, key="person_skills")
    
    # Efficiency Inputs for Selected Skills
    skills_payload = []
    if selected_skills:
        st.caption("Set Efficiency for selected skills:")
        for s_name in selected_skills:
            col_eff1, col_eff2 = st.columns([3, 1])
            with col_eff1:
                st.write(f"Efficiency for {s_name}")
            with col_eff2:
                eff = st.number_input(f"Eff ({s_name})", min_value=1, max_value=10, value=1, key=f"eff_{s_name}")
            skills_payload.append({"name": s_name, "efficiency": eff})
    
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
                if "temp_occupancies" not in st.session_state:
                    st.session_state.temp_occupancies = []
                st.session_state.temp_occupancies.append({"start": str(occ_start), "end": str(occ_end)})
            else:
                st.error("End date must be after start date.")

    if "temp_occupancies" in st.session_state and st.session_state.temp_occupancies:
        st.write("Selected Ranges:")
        for i, r in enumerate(st.session_state.temp_occupancies):
            st.write(f"{i+1}. {r['start']} to {r['end']}")
        if st.button("Clear Ranges", key="clear_occ"):
            st.session_state.temp_occupancies = []
    
    st.divider()
    if st.button("Add Person", key="add_person_btn"):
        if name and selected_skills:
            payload = {
                "name": name,
                "email": email if email else None,
                "joining_date": str(start_date),
                "termination_date": str(term_date) if term_date else None,
                "skills": skills_payload,
                "busy_ranges": st.session_state.get("temp_occupancies", [])
            }
            
            resp = create_person(payload)
            if resp.status_code == 200:
                st.success(f"Added {name}")
                st.session_state.temp_occupancies = [] 
                st.rerun()
            else:
                st.error(f"Error: {resp.text}")
        elif not name:
            st.error("Name is required.")
        elif not selected_skills:
            st.error("Select at least one skill.")

def render_edit_person_tab(skills):
    people = get_people()
    if not people:
        st.info("No people to edit.")
        return

    person_map = {p['name']: p for p in people}
    selected_name = st.selectbox("Select Person to Edit", ["-- Select --"] + sorted(list(person_map.keys())))
    
    if selected_name != "-- Select --":
        person = person_map[selected_name]
        
        # Edit Form
        st.subheader(f"Editing {person['name']}")
        
        # Delete Button (Top Level for visibility)
        if st.button("Delete Person", type="primary", key="del_person_btn"):
            from frontend.utils.api import delete_person
            resp = delete_person(person['id'])
            if resp.status_code == 200:
                st.success("Person deleted.")
                st.rerun()
            else:
                st.error(f"Error: {resp.text}")
        
        st.markdown("---")
        
        with st.form("edit_person_form"):
            new_name = st.text_input("Name", value=person['name'])
            new_email = st.text_input("Email", value=person.get('email', ''))
            
            c1, c2 = st.columns(2)
            with c1:
                join_date = date.fromisoformat(person['joining_date'])
                new_join = st.date_input("Joining Date", value=join_date)
            with c2:
                term_val = date.fromisoformat(person['termination_date']) if person['termination_date'] else None
                new_term = st.date_input("Termination Date", value=term_val) if term_val else st.date_input("Termination Date", value=None)
                # Note: streamlit date_input doesn't accept None for value easily if we want to represent "None". 
                # Improving UI: Checkbox for termination.
            
            has_term_edit = st.checkbox("Set Termination Date", value=bool(person['termination_date']))
            if not has_term_edit:
                new_term = None
            
            # Skills
            # Get current efficiencies
            current_skills_map = {s['name']: s.get('efficiency', 1) for s in person['skills']}
            current_skill_names = sorted(list(current_skills_map.keys()))
            
            all_skills = sorted([s['name'] for s in skills])
            new_skills_names = st.multiselect("Skills", all_skills, default=current_skill_names)
            
            new_skills_payload = []
            if new_skills_names:
                st.caption("Set Efficiency for selected skills:")
                for s_name in new_skills_names:
                    # preserving existing efficiency if present
                    default_eff = current_skills_map.get(s_name, 1)
                    col_eff1, col_eff2 = st.columns([3, 1])
                    with col_eff1:
                        st.write(f"Efficiency for {s_name}")
                    with col_eff2:
                        eff = st.number_input(f"Eff ({s_name})", min_value=1, max_value=10, value=default_eff, key=f"edit_eff_{person['id']}_{s_name}")
                    new_skills_payload.append({"name": s_name, "efficiency": eff})
            
            # Busy Ranges
            # Simplified: Text Area with instructions or just Re-Add?
            # Better: Show current ranges and allow clearing/replacing
            st.write("Busy Ranges (Modify to Replace All)")
            current_ranges_text = "\n".join([f"{r['start']} to {r['end']}" for r in person['busy_ranges']])
            st.text_area("Current Ranges (Read Only)", value=current_ranges_text, disabled=True)
            
            st.info("To update busy ranges, use the 'Manage Occupancies' section below the updates.")
            
            if st.form_submit_button("Update Details"):
                payload = {
                    "name": new_name,
                    "email": new_email if new_email else None,
                    "joining_date": str(new_join),
                    "termination_date": str(new_term) if new_term else None,
                    "skills": new_skills_payload
                    # busy_ranges not included here, updated separately if needed or we can merge logic
                }
                from frontend.utils.api import update_person
                resp = update_person(person['id'], payload)
                if resp.status_code == 200:
                    st.success("Details updated!")
                    st.rerun()
                else:
                    st.error(f"Error: {resp.text}")

        # Separate section for Occupancies to avoid complex form nesting state
        st.subheader("Manage Occupancies")
        st.caption("Adding ranges here will REPLACE the existing list with the new list + added ones? No, API replaces entire list if provided.")
        st.caption("Current implementation: API replaces ALL ranges if 'busy_ranges' key is present. So we must provide the FULL list.")
        
        # State management for editing ranges
        # We load existing ranges into session state if not already there for this person
        edit_key = f"edit_ranges_{person['id']}"
        if edit_key not in st.session_state:
            st.session_state[edit_key] = [{"start": r["start"], "end": r["end"]} for r in person["busy_ranges"]]
            
        ranges = st.session_state[edit_key]
        
        # Display editable list
        for i, r in enumerate(ranges):
            c_r1, c_r2 = st.columns([4, 1])
            with c_r1:
                st.write(f"{r['start']} to {r['end']}")
            with c_r2:
                if st.button("Remove", key=f"rm_rng_{person['id']}_{i}"):
                    ranges.pop(i)
                    st.rerun()
        
        # Add new
        c_add1, c_add2, c_add3 = st.columns([2, 2, 1])
        with c_add1:
            new_start = st.date_input("Start", key=f"new_start_{person['id']}")
        with c_add2:
            new_end = st.date_input("End", key=f"new_end_{person['id']}")
        with c_add3:
            st.write("")
            st.write("")
            if st.button("Add", key=f"add_rng_btn_{person['id']}"):
                ranges.append({"start": str(new_start), "end": str(new_end)})
                st.rerun()
                
        if st.button("Save Occupancies Changes"):
            from frontend.utils.api import update_person
            payload = {"busy_ranges": ranges}
            resp = update_person(person['id'], payload)
            if resp.status_code == 200:
                st.success("Occupancies updated!")
                # Clear session state
                if edit_key in st.session_state:
                    del st.session_state[edit_key]
                st.rerun()
            else:
                 st.error(f"Error: {resp.text}")

def render_manual_assignment_tab():
    st.subheader("Manual Task Assignment")
    people = get_people()
    projects = get_projects()
    
    if not people or not projects:
        st.info("Need both People and Projects to assign tasks.")
    else:
        # Select Person
        person_names_map = {p['name']: p for p in people}
        selected_person_name = st.selectbox("Select Person", list(person_names_map.keys()), key="man_assign_person")
        selected_person = person_names_map[selected_person_name]
        
        # Select Project
        project_names_map = {p['name']: p for p in projects}
        selected_project_name = st.selectbox("Select Project", list(project_names_map.keys()), key="man_assign_proj")
        selected_project = project_names_map[selected_project_name]
        
        if selected_person and selected_project:
            # Filter unassigned tasks (or tasks that need more people)
            available_tasks = []
            for t in selected_project['tasks']:
                 needed = t.get('workforce_count', 1)
                 assignees = t.get('assignees', [])
                 if len(assignees) < needed:
                     available_tasks.append(t)
                 elif st.toggle(f"Show full tasks? ({t['name']})", key=f"tog_{t['id']}"):
                     available_tasks.append(t) # Allow manual override if user toggles
                     
            if available_tasks:
                task_options = {f"{t['name']} ({t['required_skill']['name']})": t for t in available_tasks}
                selected_task_label = st.selectbox("Select Task", list(task_options.keys()), key="man_assign_task")
                selected_task = task_options[selected_task_label]
                
                if st.button("Assign Task", key="man_assign_btn"):
                    # Check eligibility (Frontend check for better UX, backend enforces anyway)
                    person_skill_names = [s['name'] for s in selected_person['skills']]
                    if selected_task['required_skill']['name'] not in person_skill_names:
                         st.warning(f"{selected_person['name']} does not have required skill: {selected_task['required_skill']['name']}")
                    else:
                         resp = assign_task(selected_task['id'], selected_person['id'])
                         if resp.status_code == 200:
                             st.success(f"Assigned '{selected_task['name']}' to {selected_person['name']}")
                             st.rerun()
                         else:
                             st.error(f"Error: {resp.text}")
            else:
                st.info("No unassigned tasks in this project.")

def render_roster():
    st.subheader("Roster & Assignments")
    people = get_people()
    if people:
        # Cross reference projects for assignments
        projects = get_projects()
        assignments_map = {p['id']: [] for p in people}
        
        if projects:
            for proj in projects:
                for t in proj['tasks']:
                    for person in t.get('assignees', []):
                        pid = person['id']
                        if pid in assignments_map:
                            assignments_map[pid].append(f"{t['name']} ({proj['name']})")

        people_data = []
        for p in people:
            skills_str = ", ".join([f"{s['name']} ({s.get('efficiency', 1)})" for s in p['skills']])
            busy_str = ", ".join([f"{r['start']} to {r['end']}" for r in p['busy_ranges']]) if p['busy_ranges'] else "None"
            avail_str = f"{p['joining_date']} -> {p['termination_date'] if p['termination_date'] else 'Indefinite'}"
            
            assigned_list = assignments_map.get(p['id'], [])
            assignments_str = ", ".join(assigned_list) if assigned_list else "None"
            
            people_data.append({
                "Name": p['name'], 
                "Email": p.get('email', ''),
                "Skills": skills_str, 
                "Skills": skills_str, 
                "Availability": avail_str,
                "Leaves": busy_str,
                "Assigned Tasks": assignments_str
            })
        st.table(pd.DataFrame(people_data))
    else:
        st.info("No people added yet.")
