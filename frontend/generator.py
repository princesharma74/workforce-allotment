from datetime import date, timedelta
import random

def generate_tasks_simulation(project_info: dict) -> list[dict]:
    """
    Simulates task generation based on project info.
    
    Args:
        project_info (dict): Dictionary containing project details like:
                             - compilers_count
                             - instances_per_compiler
                             - duration_weeks (optional, for timeline)
                             - tapeout_date (optional)
                             
    Returns:
        list[dict]: List of task dictionaries compatible with the frontend draft format.
    """
    tasks = []
    
    compilers_count = project_info.get("compilers_count", 0)
    instances_per = project_info.get("instances_per_compiler", 0)
    
    # Example logic:
    # If compilers > 0, we need "Compiler Development" tasks.
    # If instances > 0, we need "Instance Implementation" tasks.
    # We'll just generate some dummy tasks for demonstration.
    
    start_date = date.today()
    
    # 1. Architecture/Planning (Always needed)
    tasks.append({
        "name": "Architecture Planning",
        "skill_name": "Architecture", # Assuming this skill exists or will be mapped
        "required_ranges": [
            {"start": str(start_date), "end": str(start_date + timedelta(days=5))}
        ],
        "workforce_count": 1
    })
    
    # 2. Compiler Tasks
    if compilers_count > 0:
        for i in range(1, compilers_count + 1):
            tasks.append({
                "name": f"Compiler {i} Development",
                "skill_name": "Compiler Design",
                "required_ranges": [
                     {"start": str(start_date + timedelta(days=7)), "end": str(start_date + timedelta(days=21))}
                ],
                "workforce_count": 2 # Assuming 2 people per compiler
            })

    # 3. Instance/RTL Tasks
    total_instances = compilers_count * instances_per
    if total_instances > 0:
        # Batch instances for simplicity
        tasks.append({
            "name": f"RTL Implementation ({total_instances} instances)",
            "skill_name": "RTL Design",
            "required_ranges": [
                {"start": str(start_date + timedelta(days=14)), "end": str(start_date + timedelta(days=42))}
            ],
            "workforce_count": max(1, total_instances // 2) 
        })
        
    # 4. Verification
    tasks.append({
        "name": "System Verification",
        "skill_name": "Verification",
        "required_ranges": [
             {"start": str(start_date + timedelta(days=30)), "end": str(start_date + timedelta(days=60))}
        ],
        "workforce_count": 2
    })
    
    return tasks
