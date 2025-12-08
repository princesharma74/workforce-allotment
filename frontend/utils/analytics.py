from typing import List, Dict
from datetime import date, timedelta
from collections import defaultdict

# Adapted from original app/analytics.py but working with dicts from API
def calculate_supply_and_demand(projects: List[dict], people: List[dict]):
    if notProjects(projects):
        return {}

    demand_counts = defaultdict(lambda: defaultdict(int))
    
    # Calculate Demand
    for project in projects:
        for task in project.get('tasks', []):
            skill_name = task['required_skill']['name']
            for r in task.get('required_ranges', []):
                start = date.fromisoformat(r['start'])
                end = date.fromisoformat(r['end'])
                
                current = start
                count = task.get('workforce_count', 1)
                while current <= end:
                    demand_counts[skill_name][current.isoformat()] += count
                    current += timedelta(days=1)
    
    if not demand_counts:
        return {}

    all_dates_set = set()
    for skill_dates in demand_counts.values():
        all_dates_set.update(skill_dates.keys())
    
    if not all_dates_set:
        return {}
        
    sorted_dates_str = sorted(list(all_dates_set))
    min_date = date.fromisoformat(sorted_dates_str[0])
    max_date = date.fromisoformat(sorted_dates_str[-1])
    
    all_skills = set(demand_counts.keys())
    result = {}
    
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
                # Check skill
                person_skills = [s['name'] for s in person.get('skills', [])]
                if skill in person_skills:
                    # Check employment
                    join_date = date.fromisoformat(person['joining_date'])
                    term_date = date.fromisoformat(person['termination_date']) if person.get('termination_date') else None
                    
                    if d < join_date:
                        continue
                    if term_date and d > term_date:
                        continue
                    
                    # Check schedule (busy ranges)
                    is_busy = False
                    for busy in person.get('busy_ranges', []):
                        b_start = date.fromisoformat(busy['start'])
                        b_end = date.fromisoformat(busy['end'])
                        if b_start <= d <= b_end:
                            is_busy = True
                            break
                    
                    if not is_busy:
                        # Find efficiency for this skill
                        efficiency = 1
                        for s in person.get('skills', []):
                            if s['name'] == skill:
                                efficiency = s.get('efficiency', 1)
                                break
                        supply_count += efficiency
            
            skill_supply.append(supply_count)
            
        result[skill] = {
            'dates': all_dates_str,
            'demand': skill_demand,
            'supply': skill_supply
        }
            
    return result

def notProjects(p):
    return not p
