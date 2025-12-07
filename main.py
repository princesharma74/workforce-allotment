from app.scheduler import Scheduler
from app.utils import load_testcases_from_directory, print_results
from app.analytics import calculate_skill_demand, generate_html_report

def main():
    scheduler = Scheduler()
    testcases = load_testcases_from_directory("testcases")

    for name, people, projects in testcases:
        feasible, infeasible = scheduler.schedule_all(projects, people)
        print_results(name, feasible, infeasible)
        
        # Generate Skill Demand Report
        print(f"Calculating skill demand for {name}...")
        demand = calculate_skill_demand(projects)
        generate_html_report(demand, f"report_{name}.html")

if __name__ == "__main__":
    main()
