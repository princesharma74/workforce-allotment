import sys
from sqlmodel import Session, select
from backend.app.database import engine, create_db_and_tables
from backend.app.services.scheduler import SchedulerService
from backend.app.utils.loader import load_yaml_to_db
from backend.app.models import Project

def main():
    print("Initializing Database...")
    create_db_and_tables()
    
    with Session(engine) as session:
        print("Loading testcases...")
        load_yaml_to_db(session, "testcases")
        
        print("Running Scheduler...")
        scheduler = SchedulerService(session)
        feasible, infeasible = scheduler.schedule_all()
        
        print(f"\nResults:")
        print(f"Feasible Projects: {len(feasible)}")
        for p in feasible:
            print(f"  - {p.name}")
            
        print(f"Infeasible Projects: {len(infeasible)}")
        for p in infeasible:
            print(f"  - {p.name} (Reason: {p.failure_reason})")

if __name__ == "__main__":
    main()
