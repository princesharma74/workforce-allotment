# Optimization of Workforce Scheduling: From Greedy Heuristics to Exact Constraint Programming

## Abstract
This paper documents the evolution of a workforce scheduling system designed to maximize project accommodation under complex skill and efficiency constraints. We demonstrate how transitioning from a naive Greedy algorithm to a Constraint Programming (CP) model using Google OR-Tools resulted in a **70% increase in feasible project assignments** (from 10/20 to 17/20 in benchmarks). We provide a detailed implementation guide for modeling multi-skill, efficiency-weighted scheduling problems with **multi-objective optimization** (Projects > Efficiency > Workload Balancing).

---

## 1. Introduction
The core problem is a variation of the **Resource-Constrained Project Scheduling Problem (RCPSP)**.
**Objectives:** 
1. **Primary:** Maximize the number of "Active Projects".
2. **Secondary:** Minimize total assignments (prefer fewer, more efficient workers).
3. **Tertiary:** Minimize workload variance (distribute load evenly).

**Constraints:**
1.  **Skills:** People must possess the specific skill required by a task.
2.  **Efficiency Density:** A task requires a total "Efficiency Sum" (e.g., 3 units). A senior engineer might contribute 3 units, while a junior contributes 1.
3.  **Multitasking:** A person can work on multiple tasks *simultaneously* if they share the **same skill** and their total efficiency capacity is not exceeded.
4.  **Exclusive Contexts:** A person **cannot** work on tasks requiring *different skills* at the same time (Context Switching penalty/impossibility).
5.  **Workload Balancing:** The solver should minimize the variance in workload across the team.

---

## 2. The Baseline: Greedy Algorithm (First-Come-First-Served)
The initial approach iterated through projects in input order, assigning the first valid candidate found.

### The "Versatile Worker Trap"
This approach fails spectacularly when "Versatile" workers (who hold rare skills) are consumed by common tasks.

**Case Study:** `10_10_project_test_10.yaml`
*   **Alice:** Skills `[Java, SQL]`.
*   **Bob:** Skill `[Java]`.
*   **Project Requirements:** Task A (Java), Task B (SQL).

**Greedy Execution:**
1.  Scheduler attempts **Task A (Java)**.
2.  Sees **Alice**. Alice has Java. **Assigns Alice.**
3.  Scheduler attempts **Task B (SQL)**.
4.  Needs SQL. Alice is busy. Bob lacks SQL. **Project Fails.**

**Result:** 0 Feasible Projects.

---

## 3. Phase 1: Heuristic Optimization (Local Search)
To mitigate the Versatile Worker Trap, we introduced a sorting heuristic: **"Least Skills First"**.
Before assigning a task, we sort candidates by `len(skills)`.

**Heuristic Execution:**
1.  Scheduler attempts **Task A (Java)**.
2.  Candidates: Alice (2 skills), Bob (1 skill).
3.  Sorts candidates: `[Bob, Alice]`.
4.  **Assigns Bob** to Task A.
5.  Scheduler attempts **Task B (SQL)**.
6.  **Assigns Alice** (free) to Task B.
7.  **Project Succeeds.**

### Limitations
While this solved the specific case, heuristics are fundamentally **myopic**. They make local decisions without knowing if a better global trade-off exists (e.g., rejecting one medium project to fit two small ones).
*   **Benchmark Performance:** Improved from 10 to 14 feasible projects.
*   **Ceiling:** Stuck in local optima for complex efficiency packing problems.

---

## 4. The Solution: Exact Optimization (Constraint Programming)
To guarantee the **mathematically optimal** solution, we adopted **Google OR-Tools (CP-SAT)**.
Instead of *writing the steps* to find a solution (Procedural), we *describe the rules* of a valid solution and let the solver search the state space (Declarative).

### 4.1. Mathematical Formulation

**Variables:**
*   $X_p \in \{0, 1\}$: Is Project $p$ active?
*   $Y_{t,u} \in \{0, 1\}$: Is Person $u$ assigned to Task $t$?
*   $W_u$: Total workload for Person $u$.
*   $S_u$: Squared workload for Person $u$ (for variance minimization).

**Objective Function:**
$$ \text{Maximize } (C_1 \sum X_p) - (C_2 \sum Y_{t,u}) - (C_3 \sum S_u) $$

Where weights are prioritized: $C_1 \gg C_2 \gg C_3$ (e.g., $10^{12}, 10^6, 1$).
1.  **Projects:** Priority.
2.  **Assignments:** Cost (Minimize to prefer high-efficiency workers).
3.  **Workload:** Cost (Minimize sum of squares to balance load).

### 4.2. Modeling Constraints

#### A. Fulfillment Constraint
If a project is active ($X_p=1$), all its tasks must meet workforce demand:
$$ \sum_{u \in People} (Y_{t,u} \times \text{Efficiency}_{u,skill}) \ge \text{Demand}_t $$

#### B. The "Skill Context" Constraint (The Hard Part)
This is where standard Linear Programming struggles, but CP shines.
We treat a Person's time as a set of **Intervals**.

1.  **Same-Skill Multitasking (Cumulative):**
    If a person has multiple tasks for the *same skill* (e.g., Java), their total load at any time $t$ must not exceed their efficiency.
    *   **CP Tool:** `AddCumulative(intervals, demands=[1,1,...], capacity=Efficiency)`
    *   *Analogy:* Filling a bucket. You can pour multiple streams in as long as they don't overflow the rim.

3.  **Cross-Skill Conflict (No Overlap):**
    If a person has tasks for *different skills* (e.g., Java vs SQL), they cannot overlap at all.
    *   **CP Tool:** `AddNoOverlap([Interval_Java, Interval_SQL])`
    *   *Analogy:* You can't be in two rooms at once.

#### C. Workload Balancing
To ensure fair distribution of work, we calculate the total duration of all assigned tasks for each person.
*   **Variable:** `workload_sq_var = (total_days)^2`
*   **Objective:** Minimize $\sum workload\_sq\_var$
*   *Effect:* The solver prefers assigning tasks to 2 people with 5 days each ($5^2+5^2=50$) rather than 1 person with 10 days ($10^2+0^2=100$).

---

## 5. Implementation Guide
Using `ortools.sat.python.cp_model`:

```python
model = cp_model.CpModel()

# 1. Create Intervals for every potential assignment
# OptionalIntervalVar: Only exists if the assignment variable is True
opt_int = model.NewOptionalIntervalVar(start, duration, end, is_present_var, name)

# 2. Group Intervals by Skill
intervals_by_skill = { 'Java': [int1, int2], 'SQL': [int3] }

# 3. Apply Constraints
for skill, intervals in intervals_by_skill.items():
    # Efficiency Multitasking
    model.AddCumulative(intervals, [1]*len(intervals), capacity=efficiency)

# 4. Apply Cross-Skill Locks
# Pairwise NoOverlap between different skill groups
for i in intervals_by_skill['Java']:
    for j in intervals_by_skill['SQL']:
        model.AddNoOverlap([i, j])

# 5. Workload Balancing
model.AddMultiplicationEquality(workload_sq, [workload, workload])
# Add to objective (minimize sum of squares)
```

---

## 6. Results & Benchmarks
We tested the three approaches against a standardized test suite (`efficiency_test.yaml`) involving 20 complex projects with high contention.

| Approach | Feasible Projects | Improvement | Description |
| :--- | :--- | :--- | :--- |
| **Greedy** | 10 / 20 | Baseline | Reference implementation. |
| **Heuristic**| 14 / 20 | +40% | Solved versatile worker traps. |
| **CP-SAT** | **17 / 20** | **+70%** | Found non-obvious global packings. |

### Conclusion
Transitioning to an Exact Solver eliminates the "Trial and Error" of heuristic tuning. While heuristics are faster to implement initially, Constraint Programming provides:
1.  **Guaranteed Optimality:** No "maybe there's a better way".
2.  **Flexibility:** Adding a new constraint (e.g., "No more than 2 juniors per project") is adding one line of code, rather than rewriting a sorting algorithm.
