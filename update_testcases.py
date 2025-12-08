
import os
import yaml

TESTCASES_DIR = "backend/app/services/testcases"
UPDATED_COUNT = 0

def update_testcases():
    global UPDATED_COUNT
    for filename in os.listdir(TESTCASES_DIR):
        if not filename.endswith(".yaml"):
            continue
        
        filepath = os.path.join(TESTCASES_DIR, filename)
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)
        
        if not data or "projects" not in data:
            continue
            
        modified = False
        for project in data["projects"]:
            if "tasks" not in project:
                continue
            for task in project["tasks"]:
                if "workforce_count" not in task:
                    task["workforce_count"] = 1
                    modified = True
        
        if modified:
            with open(filepath, "w") as f:
                yaml.dump(data, f, sort_keys=False, default_flow_style=False)
            print(f"Updated {filename}")
            UPDATED_COUNT += 1
        else:
            print(f"Skipped {filename} (already has fields or no tasks)")

if __name__ == "__main__":
    update_testcases()
    print(f"Total updated: {UPDATED_COUNT}")
