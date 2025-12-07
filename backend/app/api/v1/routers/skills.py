from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from backend.app.database import get_session
from backend.app.models import Skill
from backend.app.schemas import SkillRead, SkillCreate, SkillUpdate

router = APIRouter(prefix="/skills", tags=["skills"])

@router.post("/", response_model=SkillRead)
def create_skill(skill: SkillCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(Skill).where(Skill.name == skill.name)).first()
    if existing:
        return existing
        
    db_skill = Skill(name=skill.name)
    session.add(db_skill)
    session.commit()
    session.refresh(db_skill)
    return db_skill

@router.get("/", response_model=List[SkillRead])
def read_skills(session: Session = Depends(get_session)):
    skills = session.exec(select(Skill)).all()
    return skills

@router.delete("/{skill_id}")
def delete_skill(skill_id: int, session: Session = Depends(get_session)):
    skill = session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    session.delete(skill)
    session.commit()
    return {"ok": True}

@router.put("/{skill_id}", response_model=SkillRead)
def update_skill(skill_id: int, skill_in: SkillUpdate, session: Session = Depends(get_session)):
    skill = session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if skill_in.name:
        skill.name = skill_in.name
    session.add(skill)
    session.commit()
    session.refresh(skill)
    return skill
