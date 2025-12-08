import streamlit as st
from app.models import Skill

def render_manage_skills():
    st.header("Manage Skills")
    
    with st.form("add_skill_form"):
        new_skill_name = st.text_input("Skill Name")
        submitted = st.form_submit_button("Add Skill")
        
        if submitted and new_skill_name:
            skill = Skill(name=new_skill_name)
            if skill not in st.session_state.skills:
                st.session_state.skills.add(skill)
                st.success(f"Added skill: {new_skill_name}")
            else:
                st.warning("Skill already exists.")
    
    st.subheader("Current Skills")
    if st.session_state.skills:
        skill_names = sorted([s.name for s in st.session_state.skills])
        st.write(", ".join(skill_names))
    else:
        st.info("No skills added yet.")
