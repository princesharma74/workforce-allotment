
import urllib.request
import json
import sys

BASE_URL = "http://localhost:8001/api/v1"

def make_request(url, method="GET", data=None):
    req = urllib.request.Request(url, method=method)
    if data:
        json_data = json.dumps(data).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
        req.data = json_data
        
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 500, str(e)

def test_scheduler_run():
    print("Testing POST /scheduler/run?dry_run=true...")
    status, data = make_request(f"{BASE_URL}/scheduler/run?dry_run=true", method="POST")
    
    if status != 200:
        print(f"FAILED: Scheduler run returned status {status}")
        print(data)
        sys.exit(1)
    
    if "feasible" not in data or "infeasible" not in data:
        print("FAILED: Response missing 'feasible' or 'infeasible' keys")
        print(data.keys())
        sys.exit(1)
        
    print(f"SUCCESS: Scheduler run returned {len(data['feasible'])} feasible and {len(data['infeasible'])} infeasible projects.")
    
    # Check structure
    if data['feasible']:
        p = data['feasible'][0]
        if 'tasks' not in p:
            print("FAILED: Feasible project missing 'tasks'")
            sys.exit(1)
        if 'feasible' not in p:
             print("FAILED: ProjectAnalysisResult should have 'feasible' field")
             sys.exit(1)
             
    if data['infeasible']:
        p = data['infeasible'][0]
        if 'failure_reason' not in p:
            print("FAILED: Infeasible project missing 'failure_reason'")
            sys.exit(1)

def test_get_projects():
    print("Testing GET /projects...")
    status, projects = make_request(f"{BASE_URL}/projects/")
    
    if status != 200:
        print(f"FAILED: Get projects returned status {status}")
        print(projects)
        sys.exit(1)
        
    print(f"SUCCESS: Retrieved {len(projects)} projects.")
    
    if projects:
        p = projects[0]
        if 'feasible' in p:
            print("FAILED: ProjectRead should NOT have 'feasible' field")
            print(p.keys())
            sys.exit(1)
        if 'failure_reason' in p:
            print("FAILED: ProjectRead should NOT have 'failure_reason' field")
            sys.exit(1)

if __name__ == "__main__":
    test_scheduler_run()
    test_get_projects()
    print("ALL TESTS PASSED")
