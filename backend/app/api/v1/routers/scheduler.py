
from typing import Dict, List, Tuple
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from backend.app.database import get_session
from backend.app.services.scheduler import SchedulerService
from backend.app.models import Project, Person, Task, PersonSkillLink
from backend.app.schemas import (
    ProjectAnalysisResult as APIProjectResult,
    TaskAnalysisResult as APITaskResult,
    PersonRead as APIPersonRead,
    SkillRead as APISkillRead,
    DateRange as APIDateRange
)
from backend.app.services.models import (
    Project as ServiceProject, 
    Person as ServicePerson, 
    Task as ServiceTask,
    Skill as ServiceSkill,
    PersonSkill as ServicePersonSkill,
    PersonBusyRange as ServiceBusyRange,
    TaskRequiredRange as ServiceAssignRange,
    TaskRequiredRange as ServiceTaskRange,
    ProjectAnalysisResult as ServiceProjectResult,
    TaskAnalysisResult as ServiceTaskResult,
    PersonRead as ServicePersonRead,
    SkillRead as ServiceSkillRead,
    DateRange as ServiceDateRange
)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

def to_service_models(db_projects: List[Project], db_people: List[Person], efficiency_map: Dict[Tuple[str, str], int]) -> Tuple[List[ServiceProject], List[ServicePerson]]:
    # Helpers to avoid duplication
    def map_person_skill(s, p_id):
        eff = efficiency_map.get((p_id, s.id), 1)
        return ServicePersonSkill(id=s.id, name=s.name, efficiency=eff)

    def map_base_skill(s):
        return ServiceSkill(id=s.id, name=s.name)
    
    def map_date_range(r, cls, **kwargs):
        # kwargs to handle different field names if any, though our models align
        return cls(start_date=r.start_date, end_date=r.end_date, **kwargs)

    # Map People
    service_people = []
    person_map = {} # id -> ServicePerson
    
    for p in db_people:
        skills = [map_person_skill(s, p.id) for s in p.skills]
        # Map manual schedule
        schedule = [map_date_range(r, ServiceBusyRange, id=r.id, person_id=p.id) for r in p.schedule]
        
        sp = ServicePerson(
            id=p.id, 
            name=p.name, 
            joining_date=p.joining_date, 
            termination_date=p.termination_date,
            skills=skills,
            schedule=schedule,
            assigned_tasks=[] # Start clean
        )
        service_people.append(sp)
        person_map[p.id] = sp
        
    # Map Projects and Tasks
    service_projects = []
    
    # helper map to find ServiceTask by id easily if needed, 
    # though we can just iterate. But we need to link tasks to people.
    all_service_tasks_map = {} 

    for proj in db_projects:
        tasks = []
        for t in proj.tasks:
            req_ranges = [map_date_range(r, ServiceTaskRange, id=r.id, task_id=t.id) for r in t.required_ranges]
            
            st = ServiceTask(
                id=t.id,
                name=t.name,
                project_id=proj.id,
                skill_id=t.skill_id,
                workforce_count=t.workforce_count,
                required_skill=map_base_skill(t.required_skill),
                required_ranges=req_ranges,
                assignees=[] # will be populated below
            )
            tasks.append(st)
            all_service_tasks_map[t.id] = st
            
        sproj = ServiceProject(id=proj.id, name=proj.name, tasks=tasks)
        service_projects.append(sproj)

    # Now populate assigned_tasks for people and assignees for tasks based on DB
    # We iterate over db_people again or iterate their assigned_tasks if available
    for p in db_people:
        sp = person_map[p.id]
        for t in p.assigned_tasks:
            if t.id in all_service_tasks_map:
                st = all_service_tasks_map[t.id]
                # bidirectional link
                sp.assigned_tasks.append(st)
                st.assignees.append(sp)
            else:
                # Task might be from a project not in db_projects list if we didn't fetch all?
                # The current run_scheduler fetches *all* projects, so this should cover everything.
                # However, if t.id is not in our map (maybe filtered out?), we should create a partial ServiceTask 
                # or similar so the person still knows they are busy.
                # Since we fetched "select(Project).all()", we have all tasks.
                pass

    return service_projects, service_people

def to_api_response(service_results: List[ServiceProjectResult]) -> List[APIProjectResult]:
    api_results = []
    
    def map_range(r) -> APIDateRange:
        return APIDateRange(start=r.start_date, end=r.end_date)
    
    def map_skill(s) -> APISkillRead:
        return APISkillRead(id=s.id, name=s.name)
        
    def map_person(p) -> APIPersonRead:
        return APIPersonRead(
            id=p.id,
            name=p.name,
            joining_date=p.joining_date,
            termination_date=p.termination_date,
            skills=[map_skill(s) for s in p.skills],
            busy_ranges=[map_range(b) for b in p.busy_ranges]
        )

    for res in service_results:
        tasks_analyzed = []
        for t in res.tasks:
            tasks_analyzed.append(APITaskResult(
                id=t.id,
                name=t.name,
                project_id=t.project_id,
                skill_id=t.skill_id,
                assignees=[map_person(p) for p in t.assignees],
                required_skill=map_skill(t.required_skill),
                required_ranges=[map_range(r) for r in t.required_ranges],
                workforce_count=t.workforce_count,
                failure_reason=t.failure_reason
            ))
            
        api_results.append(APIProjectResult(
            id=res.id,
            name=res.name,
            tasks=tasks_analyzed,
            feasible=res.feasible,
            failure_reason=res.failure_reason
        ))
    return api_results

@router.post("/run")
def run_scheduler(dry_run: bool = False, session: Session = Depends(get_session)):
    # 1. Fetch all data
    db_projects = session.exec(select(Project)).all()
    db_people = session.exec(select(Person)).all()
    db_links = session.exec(select(PersonSkillLink)).all()
    
    efficiency_map = {(l.person_id, l.skill_id): l.efficiency for l in db_links}
    
    # 2. Map to Service layer objects
    s_projects, s_people = to_service_models(db_projects, db_people, efficiency_map)
    
    # 3. Identify and filter locked tasks
    projects_to_schedule = []
    locked_tasks_map = {} # project_id -> list of ServiceTask (locked)
    
    for sp in s_projects:
        unassigned_tasks = []
        locked_tasks = []
        
        for task in sp.tasks:
            if task.assignees:
                locked_tasks.append(task)
            else:
                unassigned_tasks.append(task)
        
        if locked_tasks:
            locked_tasks_map[sp.id] = locked_tasks
            
        if unassigned_tasks:
            # Create shallow copy with only unassigned tasks
            new_sp = ServiceProject(
                id=sp.id,
                name=sp.name,
                tasks=unassigned_tasks
            )
            projects_to_schedule.append(new_sp)

    # 4. Run Scheduler
    scheduler = SchedulerService()
    feasible, infeasible = scheduler.schedule_all(projects_to_schedule, s_people)
    
    # 5. Merge locked tasks back into results
    
    def create_task_result(t: ServiceTask) -> ServiceTaskResult:
        # Map ServiceTask + assignees to ServiceTaskResult
        assignees_read = []
        for p in t.assignees:
            skills_read = [ServiceSkillRead(id=s.id, name=s.name, efficiency=s.efficiency) for s in p.skills]
            busy_read = [ServiceDateRange(start_date=b.start_date, end_date=b.end_date) for b in p.schedule]
            assignees_read.append(ServicePersonRead(
                id=p.id, name=p.name, joining_date=p.joining_date, 
                termination_date=p.termination_date, skills=skills_read, busy_ranges=busy_read
            ))
            
        req_ranges = [ServiceDateRange(start_date=r.start_date, end_date=r.end_date) for r in t.required_ranges]
        
        return ServiceTaskResult(
            id=t.id, name=t.name, project_id=t.project_id, skill_id=t.skill_id,
            assignees=assignees_read, 
            required_skill=ServiceSkillRead(id=t.required_skill.id, name=t.required_skill.name),
            required_ranges=req_ranges, workforce_count=t.workforce_count, failure_reason=None
        )

    # Add back to feasible/infeasible lists
    processed_project_ids = set()
    
    for res in feasible:
        processed_project_ids.add(res.id)
        if res.id in locked_tasks_map:
            for t in locked_tasks_map[res.id]:
                res.tasks.append(create_task_result(t))
                
    for res in infeasible:
        processed_project_ids.add(res.id)
        if res.id in locked_tasks_map:
            for t in locked_tasks_map[res.id]:
                res.tasks.append(create_task_result(t))

    # Identify projects that were skipped (fully locked)
    for sp in s_projects:
        if sp.id not in processed_project_ids and sp.id in locked_tasks_map:
            # This must be a fully locked project
            # Create a feasible result for it
            task_results = [create_task_result(t) for t in sp.tasks]
            res = ServiceProjectResult(
                id=sp.id, name=sp.name, tasks=task_results, feasible=True, failure_reason=None
            )
            feasible.append(res)
            
    # 6. If not dry_run, apply changes to DB
    if not dry_run:
        # Create lookup for db people
        db_people_map = {p.id: p for p in db_people}
        
        # Only update tasks that were actually scheduled (in feasible list)
        # But we also need to consider that "projects_to_schedule" might not be all projects.
        # We need to iterate over the results (feasible) to find what changed.
        
        for res in feasible:
            # ServiceProjectResult has tasks with assignees.
            
            # Find DB project
            db_proj = next((p for p in db_projects if p.id == res.id), None)
            if not db_proj:
                continue
                
            for task_res in res.tasks:
                db_task = next((t for t in db_proj.tasks if t.id == task_res.id), None)
                if db_task:
                    # Update assignees
                    new_assignees = []
                    for assignee_read in task_res.assignees:
                        if assignee_read.id in db_people_map:
                            new_assignees.append(db_people_map[assignee_read.id])
                    
                    db_task.assignees = new_assignees
                    session.add(db_task)
        
        session.commit()
    
    # 7. Adapt back to API Schema
    return {
        "feasible": to_api_response(feasible),
        "infeasible": to_api_response(infeasible)
    }

