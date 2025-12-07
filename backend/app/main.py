from fastapi import FastAPI
# Force reload
from contextlib import asynccontextmanager
from .database import create_db_and_tables
from backend.app.api.v1.routers import people, projects, scheduler, skills

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(people.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(scheduler.router, prefix="/api/v1")
app.include_router(skills.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Workforce Allotment API is running"}
