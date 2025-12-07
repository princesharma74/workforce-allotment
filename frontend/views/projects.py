import streamlit as st
import pandas as pd
from datetime import date, timedelta
from frontend.utils.api import get_skills, get_projects, create_project

def render_manage_projects():
    st.header("Manage Projects")
    
    skills = get_skills()
    if not skills:
        st.error("Please add skills first.")
    else:
        tab1, tab2 = st.tabs(["Create Project", "Manage Projects"])
        
        with tab1:
            render_create_project_tab(skills)
            
        with tab2:
            render_manage_projects_tab(skills)

def render_create_project_tab(skills):
    project_name = st.text_input("Project Name")
    
    st.subheader("Add Tasks to Project")
    
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    with c1:
        task_name = st.text_input("Task Name", key="task_name_input")
    with c2:
        skill_options = sorted([s['name'] for s in skills])
        required_skill_name = st.selectbox("Required Skill", skill_options, key="task_skill_input")
    with c3:
        date_range = st.date_input("Period", value=(date.today(), date.today() + timedelta(days=1)), key="task_date_input")
    
    with c4:
        st.write("") 
        st.write("")
        add_task_btn = st.button("Add Task")
    
    if add_task_btn:
        if not project_name:
            st.error("Please enter a project name first.")
        elif not task_name:
            st.error("Please enter a task name.")
        else:
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start, end = date_range
                if "temp_tasks" not in st.session_state:
                        st.session_state.temp_tasks = []
                
                st.session_state.temp_tasks.append({
                    "name": task_name,
                    "skill_name": required_skill_name,
                    "required_ranges": [{"start": str(start), "end": str(end)}]
                })
                st.success(f"Task '{task_name}' added to draft.")
            else:
                st.error("Please select a valid date range (Start and End).")

    if "temp_tasks" in st.session_state and st.session_state.temp_tasks:
        st.markdown("##### Tasks in Draft")
        draft_data = []
        for t in st.session_state.temp_tasks:
            ranges_str = ", ".join([f"{r['start']} to {r['end']}" for r in t['required_ranges']])
            draft_data.append({"Task": t['name'], "Skill": t['skill_name'], "Period": ranges_str})
        st.table(pd.DataFrame(draft_data))
        
        if st.button("Save Project"):
            if project_name:
                payload = {
                    "name": project_name,
                    "tasks": st.session_state.temp_tasks
                }
                resp = create_project(payload)
                if resp.status_code == 200:
                    st.success(f"Project '{project_name}' saved!")
                    st.session_state.temp_tasks = [] 
                    st.rerun()
                else:
                    st.error(f"Error: {resp.text}")
            else:
                st.error("Project Name required.")
def render_manage_projects_tab(skills):
    projects = get_projects()
    if not projects:
        st.info("No projects created.")
        return

    # Select Project
    proj_map = {p['name']: p for p in projects}
    selected_p_name = st.selectbox("Select Project to Manage", ["-- Select --"] + sorted(list(proj_map.keys())))
    
    if selected_p_name != "-- Select --":
        project = proj_map[selected_p_name]
        
        # 1. Project Level Actions
        st.subheader(f"Manage: {project['name']}")
        
        with st.expander("Project Settings", expanded=False):
            new_p_name = st.text_input("Rename Project", value=project['name'])
            c_upd, c_del = st.columns(2)
            with c_upd:
                if st.button("Update Name"):
                    from frontend.utils.api import update_project
                    resp = update_project(project['id'], {"name": new_p_name})
                    if resp.status_code == 200:
                        st.success("Project renamed.")
                        st.rerun()
                    else:
                        st.error(f"Error: {resp.text}")
            with c_del:
                if st.button("Delete Project", type="primary"):
                    from frontend.utils.api import delete_project
                    resp = delete_project(project['id'])
                    if resp.status_code == 200:
                        st.success("Project deleted.")
                        st.rerun()
                    else:
                        st.error(f"Error: {resp.text}")

        # 2. Task Level Actions
        st.markdown("### Tasks")
        if not project['tasks']:
            st.info("No tasks in this project.")
        else:
            for task in project['tasks']:
                with st.expander(f"Task: {task['name']} ({task['required_skill']['name']})"):
                    # Edit Form
                    # Using a form to group updates
                    with st.form(f"edit_task_{task['id']}"):
                        t_name = st.text_input("Name", value=task['name'])
                        all_skills = sorted([s['name'] for s in skills])
                        # Handle case where skill might be deleted? Assuming skills exist if returned by API.
                        try:
                            s_idx = all_skills.index(task['required_skill']['name'])
                        except:
                            s_idx = 0
                        t_skill = st.selectbox("Skill", all_skills, index=s_idx)
                        
                        # Ranges - Simplified: Clear and Add New (One Range for now as per UI simplicity)
                        # We show current ranges string
                        c_rng_str = ", ".join([f"{r['start']} to {r['end']}" for r in task['required_ranges']])
                        st.text(f"Current Dates: {c_rng_str}")
                        
                        st.write("Update Dates (Leave unchecked to keep current)")
                        update_dates = st.checkbox("Update Dates?", key=f"chk_dates_{task['id']}")
                        new_start = None
                        new_end = None
                        if update_dates:
                            d1, d2 = st.columns(2)
                            with d1:
                                new_start = st.date_input("Start", key=f"t_start_{task['id']}")
                            with d2:
                                new_end = st.date_input("End", key=f"t_end_{task['id']}")
                        
                        submit_update = st.form_submit_button("Update Task")
                        
                        if submit_update:
                            payload = {
                                "name": t_name,
                                "skill_name": t_skill
                            }
                            if update_dates and new_start and new_end:
                                payload["required_ranges"] = [{"start": str(new_start), "end": str(new_end)}]
                            
                            from frontend.utils.api import update_task
                            resp = update_task(task['id'], payload)
                            if resp.status_code == 200:
                                st.success("Task updated!")
                                st.rerun()
                            else:
                                st.error(f"Error: {resp.text}")
                    
                    if st.button("Delete Task", key=f"del_task_{task['id']}", type="primary"):
                         from frontend.utils.api import delete_task
                         resp = delete_task(task['id'])
                         if resp.status_code == 200:
                             st.success("Task deleted.")
                             st.rerun()
                         else:
                             st.error(f"Error: {resp.text}")
