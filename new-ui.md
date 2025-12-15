# Product Context: Workforce Allotment System

## 1. Product Vision
"Workforce Allotment" is an intelligent resource management platform designed to optimize the assignment of skilled personnel to complex engineering projects. The goal is to maximize workforce utilization while ensuring every project has the right talent at the right time.

We are building a modern, premium web application that empowers resource managers to visualize supply and demand, manage project timelines, and automate the complexity of staff allocation.

## 2. Core Features & User Stories

### A. Intelligent Dashboard
**"The Control Room"**
*   **Goal:** Provide an immediate, high-level view of the organization's health.
*   **Key Insights:**
    *   **Supply vs. Demand:** Visual charts showing total available engineering hours vs. project requirements over time.
    *   **Utilization Rates:** Heatmaps or indicators showing how "busy" the workforce is.
    *   **Critical Alerts:** Notifications for unassigned tasks or projects at risk of missing deadlines due to staffing shortages.

### B. Project Management Suite
**"Defining the Work"**
*   **Goal:** A rich interface to create and manage the lifecycle of projects.
*   **Functionality:**
    *   **Project Creation:** Input key metadata (Tapeout dates, design types, priority).
    *   **Task Breakdown:** Define specific tasks within a project.
        *   *Example:* "Compiler Design" requires "Senior Engineer" for "Weeks 1-4".
    *   **Timeline Management:** Gantt-style or calendar views to visualize project duration and task dependencies.

### C. Workforce Directory
**"Knowing Your Team"**
*   **Goal:** A centralized database of human resources.
*   **Functionality:**
    *   **Profiles:** View employee details, including their primary skills and efficiency ratings.
    *   **Skill Matrix:** Manage the library of available skills (e.g., Python, C++, Verilog) and tag employees accordingly.

### D. The Scheduler (The "Magic")
**"Automated Assignment"**
*   **Goal:** Solve the puzzle of matching people to tasks.
*   **Experience:** The user should be able to trigger an "Auto-Schedule" process. The system then intelligently assigns available people to active tasks based on skills and availability, highlighting any conflicts that need manual resolution.

## 3. Design Aesthetic & Experience
We want to move away from traditional, clunky enterprise tools. The "Workforce Allotment" app should feel:

*   **Premium & Modern:** Use a sophisticated color palette (e.g., deep navys, slate grays, with vibrant accent colors for status).
*   **Clean & Uncluttered:** Data-heavy tables should be readable and spacious.
*   **Interactive:**
    *   Drag-and-drop capabilities for rescheduling tasks.
    *   Immediate visual feedback (hover states, smooth transitions).
    *   Data visualizations that are interactive (zoom, filter, drill-down).

## 4. Target User
*   **Primary:** Resource Managers, Engineering Directors.
*   **Needs:** They value speed, clarity, and trust in the data. They need to answer "Do we have enough people?" in seconds, not hours.
