
from frontend.utils.analytics import calculate_supply_and_demand
from datetime import date

def test_demand_calculation():
    # Mock Data
    projects = [
        {
            "name": "Project 1",
            "tasks": [
                {
                    "name": "Task 1",
                    "required_skill": {"id": 1, "name": "Python"},
                    "required_ranges": [{"start": "2024-01-01", "end": "2024-01-02"}],
                    "workforce_count": 2
                }
            ]
        }
    ]
    people = [] # We only check demand, so people can be empty

    # Calculate
    result = calculate_supply_and_demand(projects, people)
    
    # Verify
    if "Python" not in result:
        print("FAILURE: Python skill not found in result.")
        return

    python_data = result["Python"]
    dates = python_data["dates"]
    demand = python_data["demand"]
    
    # Debug print
    print(f"Dates: {dates}")
    print(f"Demand: {demand}")

    # Expect dates 2024-01-01 and 2024-01-02
    if "2024-01-01" not in dates or "2024-01-02" not in dates:
         print("FAILURE: Expected dates missing.")
         return

    idx1 = dates.index("2024-01-01")
    idx2 = dates.index("2024-01-02")
    
    val1 = demand[idx1]
    val2 = demand[idx2]
    
    if val1 == 2 and val2 == 2:
        print("SUCCESS: Demand is correctly 2 for both days.")
    else:
        print(f"FAILURE: Expected demand 2, got {val1} and {val2}.")

if __name__ == "__main__":
    test_demand_calculation()
