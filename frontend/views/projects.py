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
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1, 1])
    with c1:
        task_name = st.text_input("Task Name", key="task_name_input")
    with c2:
        skill_options = sorted([s['name'] for s in skills])
        required_skill_name = st.selectbox("Required Skill", skill_options, key="task_skill_input")
    with c3:
        # Initial data for the data editor
        default_data = pd.DataFrame(
            [
                {"start": date.today(), "end": date.today() + timedelta(days=1)}
            ]
        )
        # Use data_editor to allow adding multiple ranges
        edited_df = st.data_editor(
            default_data,
            num_rows="dynamic",
            width="stretch",
            key="task_ranges_editor",
            column_config={
                "start": st.column_config.DateColumn("Start Date", required=True),
                "end": st.column_config.DateColumn("End Date", required=True)
            }
        )
    with c4:
        workforce_count = st.number_input("Count", min_value=1, value=1, key="task_wf_count")
    
    with c5:
        st.write("") 
        st.write("")
        add_task_btn = st.button("Add")
    
    if add_task_btn:
        if not project_name:
            st.error("Please enter a project name first.")
        elif not task_name:
            st.error("Please enter a task name.")
        else:
            # check if edited_df is not empty
            if not edited_df.empty:
                req_ranges = []
                for idx, row in edited_df.iterrows():
                    # Handle potential NaT or None if row added but not filled, though required=True helps
                    s = row.get("start")
                    e = row.get("end")
                    if s and e:
                         req_ranges.append({"start": str(s), "end": str(e)})
                
                if req_ranges:
                    if "temp_tasks" not in st.session_state:
                         st.session_state.temp_tasks = []
                    
                    st.session_state.temp_tasks.append({
                        "name": task_name,
                        "skill_name": required_skill_name,
                        "required_ranges": req_ranges,
                        "workforce_count": workforce_count
                    })
                    st.success(f"Task '{task_name}' added to draft.")
                else:
                    st.error("Please add at least one valid date range.")
            else:
                st.error("Please add at least one valid date range.")

    if "temp_tasks" in st.session_state and st.session_state.temp_tasks:
        st.markdown("##### Tasks in Draft")
        draft_data = []
        for t in st.session_state.temp_tasks:
            ranges_str = ", ".join([f"{r['start']} to {r['end']}" for r in t['required_ranges']])
            draft_data.append({
                "Task": t['name'], 
                "Skill": t['skill_name'], 
                "Period": ranges_str,
                "Count": t.get('workforce_count', 1)
            })
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

    st.divider()
    st.subheader("Existing Projects")
    projects = get_projects()
    
    if projects:
         for p in projects:
             with st.expander(f"{p['name']} ({len(p['tasks'])} tasks)"):
                 for t in p['tasks']:
                     assignees_list = t.get('assignees', [])
                     if assignees_list:
                         names = [ps['name'] for ps in assignees_list]
                         assigned = ", ".join(names)
                     else:
                         assigned = "Unassigned"
                     
                     wc = t.get('workforce_count', 1)
                     if t['required_ranges']:
                         ranges_str = ", ".join([f"{r['start']} to {r['end']}" for r in t['required_ranges']])
                         st.write(f"- **{t['name']}** (Needs {wc}): {t['required_skill']['name']} ({ranges_str}) -> {assigned}")
                     else:
                         st.write(f"- **{t['name']}** (Needs {wc}): {t['required_skill']['name']} (No dates) -> {assigned}")
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
                        t_skill = st.selectbox("Skill", all_skills, index=s_idx, key=f"ts_{task['id']}")
                        
                        t_count = st.number_input("Workforce Count", min_value=1, value=task.get('workforce_count', 1), step=1, key=f"tc_{task['id']}")
                        
                        # Ranges - Multi-row editor
                        st.subheader("Required Periods")
                        
                        # Prepare initial data frame for editor
                        existing_ranges_data = []
                        if task.get('required_ranges'):
                            for r in task['required_ranges']:
                                try:
                                    s_d = date.fromisoformat(r['start'])
                                    e_d = date.fromisoformat(r['end'])
                                    existing_ranges_data.append({"start": s_d, "end": e_d})
                                except ValueError:
                                    pass
                        else:
                             # Default empty row if none
                             existing_ranges_data.append({"start": date.today(), "end": date.today()})
                        
                        df_ranges = pd.DataFrame(existing_ranges_data)
                        
                        edited_ranges_df = st.data_editor(
                             df_ranges,
                             num_rows="dynamic",
                             use_container_width=True,
                             key=f"editor_ranges_{task['id']}",
                             column_config={
                                "start": st.column_config.DateColumn("Start Date", required=True),
                                "end": st.column_config.DateColumn("End Date", required=True)
                             }
                        )
                        
                        submit_update = st.form_submit_button("Update Task")
                        
                        if submit_update:
                            # Parse ranges from editor
                            new_ranges_payload = []
                            if not edited_ranges_df.empty:
                                for i, row in edited_ranges_df.iterrows():
                                    s = row.get("start")
                                    e = row.get("end")
                                    if s and e:
                                        new_ranges_payload.append({"start": str(s), "end": str(e)})
                            
                            payload = {
                                "name": t_name,
                                "skill_name": t_skill,
                                "workforce_count": t_count,
                                "required_ranges": new_ranges_payload
                            }
                            
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
