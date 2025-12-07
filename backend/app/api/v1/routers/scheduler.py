from fastapi import APIRouter, Depends
from sqlmodel import Session
from backend.app.database import get_session
from backend.app.services.scheduler import SchedulerService
from backend.app.schemas import ProjectRead
from backend.app.api.v1.routers.projects import _project_to_read

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

@router.post("/run")
def run_scheduler(dry_run: bool = False, session: Session = Depends(get_session)):
    scheduler = SchedulerService(session)
    feasible, infeasible = scheduler.schedule_all(commit=not dry_run)
    
    return {
        "feasible": feasible,
        "infeasible": infeasible
    }
