import streamlit as st
import pandas as pd
from datetime import date, timedelta
from app.models import Project, Task, DateRange
from app.utils import get_skill_by_name, clear_temp_tasks

def render_manage_projects():
    st.header("Manage Projects")
    
    if not st.session_state.skills:
        st.error("Please add skills first.")
    else:
        # Project Details
        project_name = st.text_input("Project Name")
        
        st.subheader("Add Tasks to Project")
        
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            task_name = st.text_input("Task Name", key="task_name_input")
        with c2:
            skill_options = sorted([s.name for s in st.session_state.skills])
            required_skill_name = st.selectbox("Required Skill", skill_options, key="task_skill_input")
        with c3:
            # Range
            date_range = st.date_input("Period", value=(date.today(), date.today() + timedelta(days=1)), key="task_date_input")
        
        with c4:
            st.write("") # Spacer
            st.write("")
            add_task_btn = st.button("Add Task")
        
        if add_task_btn:
            if not project_name:
                st.error("Please enter a project name first.")
            elif not task_name:
                st.error("Please enter a task name.")
            else:
                # Validate date range
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start, end = date_range
                    required_skill = get_skill_by_name(required_skill_name)
                    new_task = Task(name=task_name, required_skill=required_skill, required_ranges=[DateRange(start, end)])
                    st.session_state.temp_tasks.append(new_task)
                    st.success(f"Task '{task_name}' added to draft.")
                else:
                    st.error("Please select a valid date range (Start and End).")

        # List Draft Tasks
        if st.session_state.temp_tasks:
            st.markdown("##### Tasks in Draft")
            draft_data = []
            for t in st.session_state.temp_tasks:
                ranges_str = ", ".join([f"{r.start} to {r.end}" for r in t.required_ranges])
                draft_data.append({"Task": t.name, "Skill": t.required_skill.name, "Period": ranges_str})
            st.table(pd.DataFrame(draft_data))
            
            if st.button("Save Project"):
                if project_name:
                    # New Project logic handles task linkage via __post_init__
                    new_project = Project(name=project_name, tasks=list(st.session_state.temp_tasks))
                    st.session_state.projects.append(new_project)
                    clear_temp_tasks()
                    st.success(f"Project '{project_name}' saved!")
                    st.rerun()
                else:
                    st.error("Project Name required.")

        st.divider()
        st.subheader("Existing Projects")
        if st.session_state.projects:
             for p in st.session_state.projects:
                 with st.expander(f"{p.name} ({len(p.tasks)} tasks)"):
                     for t in p.tasks:
                         st.write(f"- **{t.name}**: {t.required_skill.name} ({t.required_ranges[0].start} to {t.required_ranges[0].end})")
