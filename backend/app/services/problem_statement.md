# Problem Statement: Workforce Allocation & Scheduling

## 1. Context
The goal of the Workforce Allotment system is to intelligently assign a finite workforce of people to a set of potential projects. This is a resource allocation problem where we must decide **which projects to accept** and **who works on what**, all while respecting time, skill, and capacity constraints.

The problem is solved using **Constraint Programming (CP)** (specifically Google OR-Tools CP-SAT solver), which guarantees a mathematically optimal solution rather than an approximation.

## 2. Entities & Data Model

### 2.1 Person (The Supply)
Each candidate in the workforce possesses:
*   **Skills**: A specific set of capabilities (e.g., "Python", "React", "Data Science").
*   **Efficiency (Capacity)**: A numeric rating (integer) for each skill, representing their **concurrent workforce capacity**.
    *   *Definition*: Efficiency `n` for skill `s` means the person can fulfill a total `workforce_count` of `n` simultaneously for tasks requiring skill `s`.
    *   *Example*: A Senior Dev with Efficiency=2 in Python can:
        *   Handle 1 task requiring `workforce_count=2`.
        *   OR Handle 2 simultaneous tasks each requiring `workforce_count=1`.
*   **Availability**:
    *   **Employment Window**: Defined by `Joining Date` and optional `Termination Date`.
    *   **Busy Ranges**: Specific date ranges where the person is unavailable (leaves, holidays, etc.).
*   **Preferences**: A score indicating how much they prefer using a specific skill.

### 2.2 Project (The Demand)
A project represents a potential unit of business value.
*   **All-or-Nothing**: A project is either fully scheduled (all tasks staffed) or completely rejected. Partial completion is not useful.
*   **Composition**: A project consists of multiple **Tasks**.

### 2.3 Task
A task is a specific requirement within a project.
*   **Skill Requirement**: The specific skill needed to perform this task.
*   **Workforce Count (Load)**: The amount of "Efficiency Capacity" this task consumes from an assignee.
    *   *Implication*: If a task requires `workforce_count=1`, it "consumes" 1 unit of the assignee's efficiency for that skill during the task duration.
*   **Time Ranges**: A list of specific date intervals (Start, End) when this task must be performed.

## 3. Constraints (Hard Rules)
The scheduler must respect these inviolable rules. If a solution violates any of these, it is invalid.

1.  **Skill Validity**: A person can only be assigned to a task if they explicitly possess the required skill.
2.  **Employment Validity**: A person can only be assigned during dates that fall within their employment window (Joining to Termination).
3.  **Availability**: A person cannot be assigned to a task if they are unavailable due to defined `Busy Ranges`, already fully allocated to other tasks, or if their remaining capacity (efficiency) for the skill is insufficient to meet the task requirements.
4.  **Capacity Constraint (Same-Skill Multitasking)**:
    *   A person **CAN** work on multiple tasks simultaneously **if and only if**:
        *   All overlapping tasks require the **SAME skill**.
        *   The sum of `workforce_count` for all overlapping tasks does not exceed the person's `Efficiency` for that skill.
5.  **Exclusive Contexts (Cross-Skill Conflict)**:
    *   A person **CANNOT** work on tasks requiring **DIFFERENT skills** at the same time.
    *   *Reason*: Context switching between different domains (e.g., Coding vs. Management) is not permitted concurrently.
6.  **Task Fulfillment**: If a Project is selected:
    *   Every Task within that Project must be fully staffed (total capacity allocated $\ge$ required workforce count). This requirement can be satisfied by a single person (if their efficiency is sufficient) or multiple people.
    *   If even one task cannot be fulfilled, the entire Project is marked infeasible.

## 4. Optimization Objectives (Soft Targets)
There are billions of valid ways to assign people. The "Best" solution is defined by a weighted objective function that prioritizes:

### Priority 1: Maximize Projects (Weight: $10^{12}$)
*   **Goal**: Accommodate the highest possible number of projects.
*   **Reasoning**: This is the primary business metric. Usage of resources is secondary to delivering value.

### Priority 2: Maximize Preference (Weight: $10^3$)
*   **Goal**: Assign tasks that align with employee preferences.
*   **Reasoning**: Improves employee satisfaction and retention.

### Priority 3: Balance Workload (Weight: 1)
*   **Goal**: Minimize the variance in total days worked across the workforce.
*   **Implementation**: Minimize the sum of squared workload ($\sum W_u^2$).
*   **Reasoning**: Prevents burnout by ensuring work is distributed as evenly as possible, all else being equal.

## 5. Algorithmic Approach
The problem addresses the **Versatile Worker Trap** by using **CP-SAT (Constraint Programming)**.

*   **Cumulative Constraints**: Used to model the "Efficiency Capacity" for specific skills, allowing efficient packing of multiple small tasks into a high-efficiency worker's schedule.
*   **NoOverlap Constraints**: Used to enforce the "Exclusive Contexts" rule between different skills.
*   **Global Optimization**: The solver views the entire timeline to ensure scarce resources are allocated optimally to maximize total project throughput.
