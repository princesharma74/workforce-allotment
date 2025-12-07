from datetime import date
from app.analytics import calculate_skill_demand, generate_html_report
from app.models import Project, Task, Skill, DateRange
import os

def test_analytics():
    # Setup Data
    s1 = Skill("Python")
    s2 = Skill("Java")
    
    # Project 1: Python from Jan 1-3
    t1 = Task("T1", s1, [DateRange(date(2024, 1, 1), date(2024, 1, 3))])
    p1 = Project("P1", [t1])
    
    # Project 2: Python from Jan 2-4, Java from Jan 4-5
    t2 = Task("T2", s1, [DateRange(date(2024, 1, 2), date(2024, 1, 4))])
    t3 = Task("T3", s2, [DateRange(date(2024, 1, 4), date(2024, 1, 5))])
    p2 = Project("P2", [t2, t3])
    
    projects = [p1, p2]
    
    # Execute Function
    demand = calculate_skill_demand(projects)
    
    # Verify
    # Python Demand:
    # 2024-01-01: 1 (T1)
    # 2024-01-02: 2 (T1 + T2)
    # 2024-01-03: 2 (T1 + T2)
    # 2024-01-04: 1 (T2)
    # 2024-01-05: 0
    
    # Java Demand:
    # ...
    # 2024-01-04: 1 (T3)
    # 2024-01-05: 1 (T3)
    
    print("Demand:", demand)
    
    assert demand["Python"]["2024-01-01"] == 1
    assert demand["Python"]["2024-01-02"] == 2
    assert demand["Python"]["2024-01-03"] == 2
    assert demand["Python"]["2024-01-04"] == 1
    assert demand["Python"]["2024-01-05"] == 0
    
    assert demand["Java"]["2024-01-04"] == 1
    assert demand["Java"]["2024-01-05"] == 1
    assert demand["Java"]["2024-01-01"] == 0

    print("Verification Passed!")
    
    # Test Report Generation
    generate_html_report(demand, "test_report.html")
    assert os.path.exists("test_report.html")
    with open("test_report.html", "r") as f:
        content = f.read()
        assert "chart.js" in content
        assert "2024-01-02" in content
    print("Report generation verified!")

if __name__ == "__main__":
    test_analytics()
