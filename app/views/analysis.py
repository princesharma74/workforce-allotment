import streamlit as st
import pandas as pd
import plotly.express as px
import copy
from app.scheduler import Scheduler
from app.analytics import calculate_supply_and_demand
from app.utils import get_person_by_name, get_project_by_name

def render_analysis():
    st.header("Feasibility Analysis")
    
    if st.button("Run Scheduler"):
        scheduler = Scheduler()
        people_copy = copy.deepcopy(st.session_state.people)
        projects_copy = copy.deepcopy(st.session_state.projects)
        
        feasible, infeasible = scheduler.schedule_all(projects_copy, people_copy)
        
        # Store results in session state to allow "Confirmation"
        st.session_state.scheduler_results = (feasible, infeasible, people_copy)

    if st.session_state.scheduler_results:
        feasible, infeasible, scheduled_people = st.session_state.scheduler_results
        
        st.subheader("Results Overview")
        col1, col2 = st.columns(2)
        
        with col1:
            st.success(f"Feasible Projects: {len(feasible)}")
            for p in feasible:
                with st.expander(f"✅ {p.name}"):
                    for t in p.tasks:
                        assigned_to = t.assigned_person.name if t.assigned_person else "Unassigned"
                        st.write(f"- {t.name}: Assigned to **{assigned_to}**")
        
        with col2:
            st.error(f"Infeasible Projects: {len(infeasible)}")
            for p in infeasible:
                with st.expander(f"❌ {p.name}"):
                    st.write(f"Reason: {p.failure_reason}")
                    if p.failed_tasks:
                        st.write("Failed Tasks:")
                        for t in p.failed_tasks:
                             st.write(f"- {t.name} ({t.required_skill.name})")

        st.info("These results are simulated. To apply these assignments to the main roster, click Confirm below.")
        if st.button("Confirm & Apply assignments"):
            cnt_assignments = 0
            
            # Apply assignments to existing objects to preserve any other state if any.
            # Iterate through FEASIBLE projects (which are copies).
            # Find corresponding REAL project.
            # Find corresponding REAL task.
            # Find corresponding REAL person.
            # Assign.
            
            for p_feasible in feasible:
                real_project = get_project_by_name(p_feasible.name)
                if real_project:
                    for t_feasible in p_feasible.tasks:
                        if t_feasible.assigned_person:
                            real_task = next((rt for rt in real_project.tasks if rt.name == t_feasible.name), None)
                            real_person = get_person_by_name(t_feasible.assigned_person.name)
                            
                            if real_task and real_person:
                                # Avoid double assignment if already assigned
                                if real_task not in real_person.assigned_tasks:
                                    real_person.assign_task(real_task)
                                    cnt_assignments += 1
            
            st.session_state.scheduler_results = None # Clear results
            st.success(f"Applied {cnt_assignments} assignments successfully!")
            st.rerun()

    st.divider()
    st.header("Skill Demand & Supply Analytics")
    
    if st.session_state.projects:
        # Use fresh people list (without task assignments) to calculate base supply
        data = calculate_supply_and_demand(st.session_state.projects, st.session_state.people)
        
        if data:
            st.write("Below charts show the **Demand** (Required Resource Count) vs **Available Workforce** (Supply) for each skill.")
            
            for skill, info in data.items():
                dates = info['dates']
                demand_vals = info['demand']
                supply_vals = info['supply']
                
                # Structure for one chart
                chart_data = []
                for i, d_str in enumerate(dates):
                    chart_data.append({"Date": d_str, "Type": "Demand", "Count": demand_vals[i]})
                    chart_data.append({"Date": d_str, "Type": "Available Workforce", "Count": supply_vals[i]})
                
                df = pd.DataFrame(chart_data)
                
                fig = px.line(
                    df, 
                    x="Date", 
                    y="Count", 
                    color="Type", 
                    title=f"{skill} - Demand vs Supply",
                    markers=True,
                    color_discrete_map={"Demand": "red", "Available Workforce": "green"}
                )
                
                # Updated to use width='stretch' instead of use_container_width=True
                st.plotly_chart(fig, width="stretch")
                
        else:
            st.info("No demand data generated.")
    else:
        st.info("Add projects to see analytics.")
