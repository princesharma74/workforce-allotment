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
