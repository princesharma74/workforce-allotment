from typing import List, Dict, Set
from datetime import date, timedelta
from collections import defaultdict
import json
from .models import Project, Skill

def calculate_skill_demand(projects: List[Project]) -> Dict[str, Dict[str, int]]:
    """
    Calculates daily demand for each skill based on projects.
    Returns: Dict[skill_name, Dict[date_iso_str, count]]
    """
    if not projects:
        return {}
        
    demand_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    # Iterate through all tasks and populate demand
    for project in projects:
        for task in project.tasks:
            skill_name = task.required_skill.name
            for r in task.required_ranges:
                current = r.start
                while current <= r.end:
                    demand_counts[skill_name][current.isoformat()] += 1
                    current += timedelta(days=1)
    
    return demand_counts

def calculate_supply_and_demand(projects: List[Project], people: List['Person']) -> Dict[str, Dict[str, List]]:
    """
    Calculates daily supply and demand for each skill.
    Returns: Dict[skill_name, {
        'dates': List[str],
        'demand': List[int],
        'supply': List[int]
    }]
    """
    demand_counts = calculate_skill_demand(projects)
    if not demand_counts:
        return {}
    
    # Determine global date range from demand_counts
    all_dates_set = set()
    for skill_dates in demand_counts.values():
        all_dates_set.update(skill_dates.keys())
    
    if not all_dates_set:
        return {}
        
    sorted_dates_str = sorted(list(all_dates_set))
    min_date = date.fromisoformat(sorted_dates_str[0])
    max_date = date.fromisoformat(sorted_dates_str[-1])
    
    # 3. Calculate Supply and Final Structure
    # Supply = Count of people who have the skill AND are available (not busy/terminated)
    
    all_skills = set(demand_counts.keys())
    result = {}
    
    # Generate all dates
    all_dates_obj = []
    curr = min_date
    while curr <= max_date:
        all_dates_obj.append(curr)
        curr += timedelta(days=1)
        
    all_dates_str = [d.isoformat() for d in all_dates_obj]
    
    for skill in all_skills:
        skill_demand = []
        skill_supply = []
        
        for d in all_dates_obj:
            d_str = d.isoformat()
            
            # Demand
            skill_demand.append(demand_counts[skill].get(d_str, 0))
            
            # Supply
            supply_count = 0
            for person in people:
                # Check if person has skill
                has_skill = False
                for s in person.skills:
                    if s.name == skill:
                        has_skill = True
                        break
                
                if has_skill:
                    # Check employment
                    if d < person.joining_date:
                        continue
                    if person.termination_date and d > person.termination_date:
                        continue
                        
                    # Check schedule (occupancy)
                    # We treat schedule entries as "busy" (unavailable)
                    is_busy = False
                    for busy_range in person.schedule:
                        # Check strictly if date falls in range
                        if busy_range.start <= d <= busy_range.end:
                            is_busy = True
                            break
                    
                    if not is_busy:
                        supply_count += 1
                        
            skill_supply.append(supply_count)
            
        result[skill] = {
            'dates': all_dates_str,
            'demand': skill_demand,
            'supply': skill_supply
        }
            
    return result

def generate_html_report(demand_data: Dict[str, Dict[str, int]], output_file: str):
    """
    Generates an HTML file with a Chart.js visualization of the skill demand.
    """
    if not demand_data:
        print(f"No data to visualize. Skipping report generation for {output_file}")
        return

    # Prepare data for Chart.js
    # We need labels (dates) and datasets (one per skill)
    
    # Extract all dates from the first skill (they should be the same)
    first_skill = next(iter(demand_data))
    dates = sorted(demand_data[first_skill].keys())
    
    datasets = []
    colors = [
        'rgba(255, 99, 132, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(75, 192, 192, 1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 159, 64, 1)'
    ]
    
    for i, (skill, counts) in enumerate(demand_data.items()):
        data_points = [counts[d] for d in dates]
        color = colors[i % len(colors)]
        datasets.append({
            'label': skill,
            'data': data_points,
            'borderColor': color,
            'backgroundColor': color.replace('1)', '0.2)'),
            'fill': False,
            'tension': 0.1
        })
        
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Skill Demand Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: sans-serif; padding: 20px; }}
        .chart-container {{ position: relative; height: 60vh; width: 90vw; }}
    </style>
</head>
<body>
    <h1>Skill Demand Over Time</h1>
    <div class="chart-container">
        <canvas id="demandChart"></canvas>
    </div>
    <script>
        const ctx = document.getElementById('demandChart').getContext('2d');
        const demandChart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(dates)},
                datasets: {json.dumps(datasets)}
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Number of People Required'
                        }},
                        ticks: {{
                            stepSize: 1
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: 'Date'
                        }}
                    }}
                }},
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Daily Demand by Skill'
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false,
                    }}
                }},
                interaction: {{
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }}
            }}
        }});
    </script>
</body>
</html>
    """
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    print(f"Report generated: {output_file}")
