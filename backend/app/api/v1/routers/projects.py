
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from backend.app.database import get_session
from backend.app.models import Project, Task, TaskRequiredRange, Skill, Person
from backend.app.schemas import ProjectCreate, ProjectRead, TaskRead, SkillRead, BulkAssignmentRequest, ProjectUpdate, TaskUpdate

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=ProjectRead)
def create_project(project_in: ProjectCreate, session: Session = Depends(get_session)):
    db_project = Project(name=project_in.name)
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    
    for t_data in project_in.tasks:
        # Resolve skill
        skill_name = t_data.skill_name
        skill = session.exec(select(Skill).where(Skill.name == skill_name)).first()
        if not skill:
            skill = Skill(name=skill_name)
            session.add(skill)
            session.commit()
            session.refresh(skill)
            
        task = Task(
            name=t_data.name,
            project_id=db_project.id,
            skill_id=skill.id
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        
        for r in t_data.required_ranges:
            tr = TaskRequiredRange(
                task_id=task.id,
                start_date=r.start,
                end_date=r.end
            )
            session.add(tr)
            
    session.commit()
    session.refresh(db_project)
    return _project_to_read(db_project)

@router.get("/", response_model=List[ProjectRead])
def read_projects(session: Session = Depends(get_session)):
    projects = session.exec(select(Project)).all()
    return [_project_to_read(p) for p in projects]

@router.delete("/{project_id}")
def delete_project(project_id: int, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
         raise HTTPException(status_code=404, detail="Project not found")
    
    # Delete tasks manually
    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    for t in tasks:
         # Delete ranges
         ranges = session.exec(select(TaskRequiredRange).where(TaskRequiredRange.task_id == t.id)).all()
         for r in ranges:
             session.delete(r)
         session.delete(t)
    
    session.delete(project)
    session.commit()
    return {"ok": True}

@router.put("/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, project_in: ProjectUpdate, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if project_in.name:
        project.name = project_in.name
    
    session.add(project)
    session.commit()
    session.refresh(project)
    return _project_to_read(project)

@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Delete ranges
    ranges = session.exec(select(TaskRequiredRange).where(TaskRequiredRange.task_id == task.id)).all()
    for r in ranges:
        session.delete(r)
        
    session.delete(task)
    session.commit()
    return {"ok": True}

@router.put("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, task_in: TaskUpdate, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
         raise HTTPException(status_code=404, detail="Task not found")
         
    if task_in.name:
        task.name = task_in.name
        
    if task_in.skill_name:
        skill = session.exec(select(Skill).where(Skill.name == task_in.skill_name)).first()
        if not skill:
            skill = Skill(name=task_in.skill_name)
            session.add(skill)
            session.commit()
            session.refresh(skill)
        task.skill_id = skill.id
        
    if task_in.required_ranges is not None:
        # Clear existing
        ranges = session.exec(select(TaskRequiredRange).where(TaskRequiredRange.task_id == task.id)).all()
        for r in ranges:
            session.delete(r)
            
        # Add new
        for rng in task_in.required_ranges:
            tr = TaskRequiredRange(
                task_id=task.id,
                start_date=rng.start,
                end_date=rng.end
            )
            session.add(tr)
            
    session.add(task)
    session.commit()
    session.refresh(task)
    
    # TaskRead requires constructing
    from backend.app.schemas import DateRange
    req_ranges = [DateRange(start=r.start_date, end=r.end_date) for r in task.required_ranges]
    
    return TaskRead(
        id=task.id,
        name=task.name,
        project_id=task.project_id,
        skill_id=task.skill_id,
        assigned_person_id=task.assigned_person_id,
        required_skill=SkillRead(id=task.required_skill.id, name=task.required_skill.name),
        required_ranges=req_ranges
    )

def _project_to_read(project: Project) -> ProjectRead:
    from backend.app.schemas import DateRange
    tasks_read = []
    for t in project.tasks:
        req_ranges = [DateRange(start=r.start_date, end=r.end_date) for r in t.required_ranges]
        tasks_read.append(TaskRead(
            id=t.id,
            name=t.name,
            project_id=project.id,
            skill_id=t.skill_id,
            assigned_person_id=t.assigned_person_id,
            required_skill=SkillRead(id=t.required_skill.id, name=t.required_skill.name),
            required_ranges=req_ranges
        ))
        
    return ProjectRead(
        id=project.id,
        name=project.name,
        tasks=tasks_read
    )

@router.put("/tasks/{task_id}/assign")
def assign_task(task_id: int, person_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    from backend.app.models import Person 
    person = session.get(Person, person_id)
    
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
        
    task.assigned_person_id = person.id
    session.add(task)
    session.commit()
    session.refresh(task)
    return {"status": "assigned", "task": task.name, "person": person.name}

@router.post("/assignments/bulk")
def bulk_assign_tasks(request: BulkAssignmentRequest, session: Session = Depends(get_session)):
    count = 0
    errors = []
    
    
    for assignment in request.assignments:
        task = session.get(Task, assignment.task_id)
        if not task:
            errors.append(f"Task {assignment.task_id} not found")
            continue
            
        person = session.get(Person, assignment.person_id)
        if not person:
            errors.append(f"Person {assignment.person_id} not found")
            continue
            
        task.assigned_person_id = person.id
        session.add(task)
        count += 1
        
    session.commit()
    return {"status": "bulk_assigned", "count": count, "errors": errors}
