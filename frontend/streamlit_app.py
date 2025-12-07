import streamlit as st
import sys
import os

# Ensure we can import from frontend package if needed, though running from root usually works
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from frontend.views.skills import render_manage_skills
from frontend.views.people import render_manage_people
from frontend.views.projects import render_manage_projects
from frontend.views.analysis import render_analysis

st.set_page_config(page_title="Workforce Allotment", layout="wide")

# Session State Init
if "temp_tasks" not in st.session_state:
    st.session_state.temp_tasks = []
if "temp_occupancies" not in st.session_state:
    st.session_state.temp_occupancies = []
if "scheduler_results" not in st.session_state:
    st.session_state.scheduler_results = None

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Manage Skills", "Manage People", "Manage Projects", "Analysis & Results"])

if page == "Manage Skills":
    render_manage_skills()
elif page == "Manage People":
    render_manage_people()
elif page == "Manage Projects":
    render_manage_projects()
elif page == "Analysis & Results":
    render_analysis()
