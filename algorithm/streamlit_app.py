import sys
import os

# Add the project root to sys.path so we can import from 'app'
# This assumes the script is located in app/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from app.utils import init_session_state
from app.views.skills import render_manage_skills
from app.views.people import render_manage_people
from app.views.projects import render_manage_projects
from app.views.analysis import render_analysis

# --- Configuration ---
st.set_page_config(page_title="Workforce Allotment", layout="wide")

# --- Session State Initialization ---
init_session_state()

# --- Sidebar ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Manage Skills", "Manage People", "Manage Projects", "Analysis & Results"])

# --- Pages ---
if page == "Manage Skills":
    render_manage_skills()
elif page == "Manage People":
    render_manage_people()
elif page == "Manage Projects":
    render_manage_projects()
elif page == "Analysis & Results":
    render_analysis()
