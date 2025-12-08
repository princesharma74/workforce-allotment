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
        
        with col1:
            st.success(f"Feasible Projects: {len(feasible)}")
            for p in feasible:
                with st.expander(f"✅ {p['name']}"):
                    for t in p['tasks']:
                        assignees_list = t.get('assignees', [])
                        if assignees_list:
                            names = [person['name'] for person in assignees_list]
                            assigned_str = f"Assigned to {', '.join(names)}"
                        else:
                            assigned_str = "Unassigned (Simulation)"
                        
                        st.write(f"- {t['name']}: {assigned_str}")
        
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

        st.info("These results are simulated. To apply these assignments to the main roster, click Confirm below.")
        if st.button("Confirm & Apply assignments"):
            with st.spinner("Applying assignments..."):
                # specific assignment logic based on simulation results
                assignments_to_apply = []
                for p in feasible:
                    for t in p['tasks']:
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
                    st.warning("No assignments to apply from the simulation.")    
    st.divider()
    st.header("Skill Demand & Supply Analytics")
    
    projects = get_projects()
    people = get_people()
    
    if projects:
        data = calculate_supply_and_demand(projects, people)
        
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
