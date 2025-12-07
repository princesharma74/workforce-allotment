import yaml
import os
from sqlmodel import Session, select
from ..models import Person, Project, Skill, Task, PersonSkillLink, PersonBusyRange, TaskRequiredRange
from datetime import datetime

def load_yaml_to_db(session: Session, directory_path: str):
    if not os.path.exists(directory_path):
        print(f"Directory not found: {directory_path}")
        return

    files = sorted([f for f in os.listdir(directory_path) if f.endswith('.yaml') or f.endswith('.yml')])
    
    for filename in files:
        file_path = os.path.join(directory_path, filename)
        print(f"Loading {filename}...")
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                
            if not data:
                continue

            # We treat each YAML as a batch of data. 
            # Note: In the old system, each YAML was a "scenario". 
            # Here we will just load everything into the persistent DB.
            # To avoid duplicates, we might want to check existence or just clear DB first.
            # For this CLI, let's just append but check for name collisions for people/projects.
            
            # Load People
            for p_data in data.get('people', []):
                # Check execution
                existing = session.exec(select(Person).where(Person.name == p_data['name'])).first()
                if existing:
                    continue
                
                person = Person(
                    name=p_data['name'],
                    joining_date=datetime.now().date() # Default if missing
                )
                session.add(person)
                session.commit()
                session.refresh(person)
                
                # Skills
                for s_name in p_data.get('skills', []):
                    skill = session.exec(select(Skill).where(Skill.name == s_name)).first()
                    if not skill:
                        skill = Skill(name=s_name)
                        session.add(skill)
                        session.commit()
                        session.refresh(skill)
                    
                    link = PersonSkillLink(person_id=person.id, skill_id=skill.id)
                    session.add(link)
                
                # Pre-booked (Busy)
                if 'pre_booked' in p_data:
                    for start_str, end_str in p_data['pre_booked']:
                        busy = PersonBusyRange(
                            person_id=person.id,
                            start_date=datetime.strptime(start_str, "%Y-%m-%d").date(),
                            end_date=datetime.strptime(end_str, "%Y-%m-%d").date()
                        )
                        session.add(busy)
            
            # Load Projects
            for proj_data in data.get('projects', []):
                existing = session.exec(select(Project).where(Project.name == proj_data['name'])).first()
                if existing:
                    continue
                    
                project = Project(name=proj_data['name'])
                session.add(project)
                session.commit()
                session.refresh(project)
                
                for t_data in proj_data.get('tasks', []):
                    s_name = t_data.get('skill')
                    skill = session.exec(select(Skill).where(Skill.name == s_name)).first()
                    if not skill:
                        skill = Skill(name=s_name)
                        session.add(skill)
                        session.commit()
                        session.refresh(skill)

                    task = Task(
                        name=t_data['name'],
                        project_id=project.id,
                        skill_id=skill.id
                    )
                    session.add(task)
                    session.commit()
                    session.refresh(task)
                    
                    for r in t_data.get('ranges', []):
                        tr = TaskRequiredRange(
                            task_id=task.id,
                            start_date=datetime.strptime(r[0], "%Y-%m-%d").date(),
                            end_date=datetime.strptime(r[1], "%Y-%m-%d").date()
                        )
                        session.add(tr)
            
            session.commit()
            
        except Exception as e:
            print(f"Error loading {filename}: {e}")
