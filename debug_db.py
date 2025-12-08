from sqlmodel import SQLModel, create_engine
from backend.app.models import Person, Skill, Project, Task, PersonSkillLink, TaskPersonLink, PersonBusyRange, TaskRequiredRange
from backend.app.database import engine

print("Imported models successfully.")

try:
    print("Creating tables...")
    SQLModel.metadata.create_all(engine)
    print("Tables created successfully.")
except Exception as e:
    print(f"Error creating tables: {e}")
