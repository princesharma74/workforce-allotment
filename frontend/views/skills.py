import streamlit as st
from frontend.utils.api import create_skill, get_skills

def render_manage_skills():
    st.header("Manage Skills")
    
    with st.form("add_skill_form"):
        new_skill_name = st.text_input("Skill Name")
        submitted = st.form_submit_button("Add Skill")
        
        if submitted and new_skill_name:
            resp = create_skill(new_skill_name)
            if resp.status_code == 200:
                st.success(f"Added skill: {new_skill_name}")
                st.rerun()
            else:
                st.error(f"Error: {resp.text}")
    
    with st.expander("Populate Default Skills"):
        if st.button("Add Standard Engineering Skills"):
            defaults = ["Architecture", "Compiler Design", "RTL Design", 
                        "Verification", "Physical Design", "Emulation", 
                        "Firmware", "Validation"]
            count = 0
            for s in defaults:
                # Naive check: just try to create, if it fails it might be because it exists
                # But to be cleaner, we can check against current list if we fetched it earlier,
                # or just fire and forget. 
                # Let's fire and forget but check status code 
                # (assuming backend handles duplicates gracefully or throws error)
                r = create_skill(s)
                if r.status_code == 200:
                    count += 1
            
            if count > 0:
                st.success(f"Added {count} new skills.")
                st.rerun()
            else:
                st.info("No new skills added (they might already exist).")
    
    st.subheader("Current Skills")
    skills = get_skills()
    if skills:
        # Display as a list with management options
        skill_options = {s['name']: s for s in skills}
        selected_skill_name = st.selectbox("Select Skill to Edit/Delete", ["-- Select --"] + sorted(list(skill_options.keys())))
        
        if selected_skill_name != "-- Select --":
            selected_skill = skill_options[selected_skill_name]
            
            with st.form("edit_skill_form"):
                st.write(f"Editing: {selected_skill['name']}")
                edit_name = st.text_input("New Name", value=selected_skill['name'])
                
                c_edit, c_del = st.columns(2)
                with c_edit:
                    update_submitted = st.form_submit_button("Update Skill")
                with c_del:
                    delete_submitted = st.form_submit_button("Delete Skill", type="primary")
                
                if update_submitted:
                    from frontend.utils.api import update_skill
                    resp = update_skill(selected_skill['id'], edit_name)
                    if resp.status_code == 200:
                        st.success("Skill updated!")
                        st.rerun()
                    else:
                        st.error(f"Error: {resp.text}")
                
                if delete_submitted:
                    from frontend.utils.api import delete_skill
                    resp = delete_skill(selected_skill['id'])
                    if resp.status_code == 200:
                        st.success("Skill deleted!")
                        st.rerun()
                    else:
                        st.error(f"Error: {resp.text}")
                        
        st.divider()
        st.write("All Skills:", ", ".join(sorted([s['name'] for s in skills])))

    else:
        st.info("No skills added yet.")
