from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from backend.app.database import get_session
from backend.app.models import Person, Skill, PersonSkillLink, PersonBusyRange
from backend.app.schemas import PersonCreate, PersonRead, SkillRead, PersonUpdate

router = APIRouter(prefix="/people", tags=["people"])

@router.post("/", response_model=PersonRead)
def create_person(person: PersonCreate, session: Session = Depends(get_session)):
    db_person = Person(
        name=person.name,
        email=person.email,
        joining_date=person.joining_date,
        termination_date=person.termination_date
    )
    session.add(db_person)
    session.commit()
    session.refresh(db_person)

    # Add skills
    for skill_input in person.skills:
        skill_name = skill_input.name
        efficiency = skill_input.efficiency
        
        skill = session.exec(select(Skill).where(Skill.name == skill_name)).first()
        if not skill:
            skill = Skill(name=skill_name)
            session.add(skill)
            session.commit()
            session.refresh(skill)
        
        # Link
        link = PersonSkillLink(
            person_id=db_person.id, 
            skill_id=skill.id, 
            efficiency=efficiency,
            preference_score=skill_input.preference_score
        )
        session.add(link)
    
    # Add busy ranges
    for rng in person.busy_ranges:
        busy = PersonBusyRange(
            person_id=db_person.id,
            start_date=rng.start,
            end_date=rng.end
        )
        session.add(busy)
    
    session.commit()
    session.refresh(db_person)
    
    # Construct response manually to handle nested lists
    return _person_to_read(db_person)

@router.get("/", response_model=List[PersonRead])
def read_people(offset: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    people = session.exec(select(Person).offset(offset).limit(limit)).all()
    return [_person_to_read(p) for p in people]

@router.delete("/{person_id}")
def delete_person(person_id: str, session: Session = Depends(get_session)):
    person = session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    # Delete links
    links = session.exec(select(PersonSkillLink).where(PersonSkillLink.person_id == person_id)).all()
    for link in links:
        session.delete(link)
        
    # Delete busy ranges
    ranges = session.exec(select(PersonBusyRange).where(PersonBusyRange.person_id == person_id)).all()
    for r in ranges:
        session.delete(r)

    session.delete(person)
    session.commit()
    return {"ok": True}

@router.put("/{person_id}", response_model=PersonRead)
def update_person(person_id: str, person_in: PersonUpdate, session: Session = Depends(get_session)):
    db_person = session.get(Person, person_id)
    if not db_person:
        raise HTTPException(status_code=404, detail="Person not found")
        
    if person_in.name is not None:
        db_person.name = person_in.name
    if person_in.email is not None:
        db_person.email = person_in.email
    if person_in.joining_date is not None:
        db_person.joining_date = person_in.joining_date
    if person_in.termination_date is not None:
        db_person.termination_date = person_in.termination_date
        
    if person_in.skills is not None:
        # Clear existing
        links = session.exec(select(PersonSkillLink).where(PersonSkillLink.person_id == person_id)).all()
        for link in links:
            session.delete(link)
        
        # Add new
        for skill_input in person_in.skills:
            skill_name = skill_input.name
            efficiency = skill_input.efficiency
            
            skill = session.exec(select(Skill).where(Skill.name == skill_name)).first()
            if not skill:
                skill = Skill(name=skill_name)
                session.add(skill)
                session.commit()
                session.refresh(skill)
            
            link = PersonSkillLink(
                person_id=db_person.id, 
                skill_id=skill.id, 
                efficiency=efficiency,
                preference_score=skill_input.preference_score
            )
            session.add(link)
            
    if person_in.busy_ranges is not None:
        # Clear existing
        ranges = session.exec(select(PersonBusyRange).where(PersonBusyRange.person_id == person_id)).all()
        for r in ranges:
            session.delete(r)
            
        # Add new
        for rng in person_in.busy_ranges:
            busy = PersonBusyRange(
                person_id=db_person.id,
                start_date=rng.start,
                end_date=rng.end
            )
            session.add(busy)

    session.add(db_person)
    session.commit()
    session.refresh(db_person)
    return _person_to_read(db_person)

def _person_to_read(person: Person) -> PersonRead:
    from backend.app.schemas import DateRange, PersonSkillRead
    
    # Map efficient
    skills_map = {l.skill_id: (l.efficiency, l.preference_score) for l in person.skill_links}
    
    skills_read = []
    for s in person.skills:
        eff, pref = skills_map.get(s.id, (1, 1))
        skills_read.append(PersonSkillRead(
            id=s.id, 
            name=s.name, 
            efficiency=eff,
            preference_score=pref
        ))
        
    return PersonRead(
        id=person.id,
        name=person.name,
        email=person.email,
        joining_date=person.joining_date,
        termination_date=person.termination_date,
        skills=skills_read,
        busy_ranges=[DateRange(start=b.start_date, end=b.end_date) for b in person.schedule]
    )
