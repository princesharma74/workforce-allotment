import yaml
import random
from datetime import date, timedelta
import argparse
import os
import sys

def generate_testcase(num_people, num_projects, max_tasks_per_project, output_file, test_case_name):
    # Ensure output directory exists if output_file has a directory component
    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    skills_pool = ["Python", "Java", "SQL", "Rust", "Go", "C++", "TypeScript", "AWS", "Docker"]
    
    # Generate People
    people = []
    for i in range(1, num_people + 1):
        num_skills = random.randint(1, 4)
        person_skill_names = random.sample(skills_pool, num_skills)
        person_skills = []
        for s_name in person_skill_names:
            efficiency = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]
            person_skills.append({"name": s_name, "efficiency": efficiency})
            
        people.append({
            "name": f"Person_{i}",
            "skills": person_skills
        })

    # Generate Projects
    projects = []
    start_date_base = date(2025, 1, 1)
    
    for i in range(1, num_projects + 1):
        tasks = []
        # Random number of tasks between 1 and max
        num_tasks = random.randint(1, max_tasks_per_project)
        for j in range(1, num_tasks + 1):
            skill = random.choice(skills_pool)
            
            # Create a random date range
            # Random start within the first 6 months
            start_offset = random.randint(0, 180)
            task_start = start_date_base + timedelta(days=start_offset)
            # Duration 1 to 14 days
            duration = random.randint(1, 14)
            task_end = task_start + timedelta(days=duration)
            
            tasks.append({
                "name": f"Task_{i}_{j}",
                "skill": skill,
                "ranges": [[str(task_start), str(task_end)]],
                "workforce_count": random.randint(1, 3)
            })
            
        projects.append({
            "name": f"Project_{i}",
            "tasks": tasks
        })

    new_testcase = {
        "name": test_case_name,
        "people": people,
        "projects": projects
    }

    # Write to file
    with open(output_file, "w") as f:
        yaml.dump(new_testcase, f, sort_keys=False, default_flow_style=False)
    
    print(f"Successfully generated '{output_file}'")
    print(f"  Test Case: {test_case_name}")
    print(f"  People: {num_people}")
    print(f"  Projects: {num_projects}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a random workforce allotment testcase.")
    
    parser.add_argument("--people", type=int, default=50, help="Number of people to generate (default: 50)")
    parser.add_argument("--projects", type=int, default=100, help="Number of projects to generate (default: 100)")
    parser.add_argument("--max-tasks", type=int, default=10, help="Maximum tasks per project (default: 10)")
    parser.add_argument("--output", type=str, default="testcases/generated_testcase.yaml", help="Output YAML file path (default: testcases/generated_testcase.yaml)")
    parser.add_argument("--name", type=str, default="Generated Test Case", help="Name of the testcase in the YAML (default: 'Generated Test Case')")

    args = parser.parse_args()
    
    generate_testcase(args.people, args.projects, args.max_tasks, args.output, args.name)
