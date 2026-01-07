uv run streamlit run frontend/streamlit_app.py --server.port 8501 &
uv run uvicorn backend.app.main:app --port 8000