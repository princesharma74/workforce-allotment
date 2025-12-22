import streamlit as st
import pandas as pd
import plotly.express as px
import copy
from frontend.utils.api import run_scheduler, get_projects, get_people, bulk_assign_tasks
from frontend.utils.analytics import calculate_supply_and_demand

def render_analysis():
    st.header("Feasibility Analysis")
    
    if st.button("Run Scheduler (Simulation)"):
        with st.spinner("Running simulation..."):
            resp = run_scheduler(dry_run=True)
            if resp.status_code == 200:
                results = resp.json()
                # Store feasible/infeasible specific lists
                st.session_state.scheduler_results = results
            else:
                st.error("Simulation failed")

    if "scheduler_results" in st.session_state and st.session_state.scheduler_results:
        results = st.session_state.scheduler_results
        feasible = results.get("feasible", [])
        infeasible = results.get("infeasible", [])
        
        st.subheader("Results Overview")
        
        # Helper to resolve names
        all_people = get_people()
        people_map = {p['id']: p['name'] for p in all_people} if all_people else {}
        
        col1, col2 = st.columns(2)
        
        # Track selected tasks
        selected_task_ids = set()

        with col1:
            st.success(f"Feasible Projects: {len(feasible)}")
            for p in feasible:
                with st.expander(f"✅ {p['name']}"):
                    st.write("Select tasks to confirm:")
                    for t in p['tasks']:
                        assignees_list = t.get('assignees', [])
                        if assignees_list:
                            names = [person['name'] for person in assignees_list]
                            assigned_str = f"Assigned to {', '.join(names)}"
                        else:
                            assigned_str = "Unassigned (Simulation)"
                        
                        # Checkbox for each task, default logic: checked if it has assignees? 
                        # User requirement: "all tasks to be assigned at once" -> "able to confirm any task specifically"
                        # Let's default to True so flow is smooth.
                        is_selected = st.checkbox(
                            f"{t['name']}: {assigned_str}", 
                            value=True, 
                            key=f"confirm_task_{t['id']}"
                        )
                        if is_selected:
                            selected_task_ids.add(t['id'])
        
        with col2:
            st.error(f"Infeasible Projects: {len(infeasible)}")
            for p in infeasible:
                with st.expander(f"❌ {p['name']}"):
                    st.write(f"Reason: {p['failure_reason']}")
                    st.markdown("#### Task Details:")
                    for t in p['tasks']:
                        if t.get('failure_reason'):
                             st.error(f"- **{t['name']}**: {t['failure_reason']}")
                        else:
                             # Optional: Show that this task was technically assignable
                             st.caption(f"- {t['name']}: Assignable (rolled back)")

        st.info(f"Selected {len(selected_task_ids)} tasks for assignment. Click Confirm below to apply.")
        if st.button("Confirm & Apply assignments"):
            with st.spinner("Applying assignments..."):
                # specific assignment logic based on simulation results AND user selection
                assignments_to_apply = []
                for p in feasible:
                    for t in p['tasks']:
                        if t['id'] in selected_task_ids:
                            for person in t.get('assignees', []):
                                assignments_to_apply.append({
                                    "task_id": t['id'],
                                    "person_id": person['id']
                                })
                
                if assignments_to_apply:
                    resp = bulk_assign_tasks(assignments_to_apply)
                    if resp.status_code == 200:
                        st.success(f"Applied {len(assignments_to_apply)} assignments successfully!")
                        if "scheduler_results" in st.session_state:
                            del st.session_state.scheduler_results
                        st.rerun()
                    else:
                        st.error(f"Failed to apply assignments: {resp.text}")
                else:
                    st.warning("No assignments selected to apply.")    
    st.divider()
    st.header("Skill Demand & Supply Analytics")
    
    current_projects = get_projects()
    people = get_people()
    
    # Merge scheduler results if available to show projected availability
    projects_for_analytics = copy.deepcopy(current_projects)
    if "scheduler_results" in st.session_state and st.session_state.scheduler_results:
        feasible = st.session_state.scheduler_results.get("feasible", [])
        # Create a map of project_id -> project from the current projects list for easier updating
        proj_map = {p['id']: p for p in projects_for_analytics}
        
        for sim_proj in feasible:
            if sim_proj['id'] in proj_map:
                # Update tasks with proposed assignees
                target_proj = proj_map[sim_proj['id']]
                # Map task_id -> task in target
                task_map = {t['id']: t for t in target_proj.get('tasks', [])}
                
                for sim_task in sim_proj.get('tasks', []):
                    if sim_task['id'] in task_map:
                        # Overwrite assignees with simulation result
                        task_map[sim_task['id']]['assignees'] = sim_task.get('assignees', [])

    if projects_for_analytics:
        data = calculate_supply_and_demand(projects_for_analytics, people)
        
        if data:
            st.write("Below charts show the **Demand** vs **Available Workforce** for each skill.")
            
            for skill, info in data.items():
                dates = info['dates']
                demand_vals = info['demand']
                supply_vals = info['supply']
                
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
                st.plotly_chart(fig, width="stretch")
        else:
            st.info("No demand data generated.")
    else:
        st.info("Add projects to see analytics.")
