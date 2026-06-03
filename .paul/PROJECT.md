# autograder

## What This Is

A web system for autograding concurrent programming assignments in C/C++. Students submit their GitHub repositories with identification; the system clones the repo, compiles the code, runs it against test cases, and records grades. Professors see results in a dashboard.

## Core Value

Students get immediate feedback on concurrent programming assignments without manual grading.

## Current State

| Attribute | Value |
|-----------|-------|
| Type | Application |
| Version | 0.0.0 |
| Status | Initializing |
| Last Updated | 2026-06-03 |

## Requirements

### Core Features

- Student submits GitHub repo URL with identification
- System clones repo, compiles C/C++ code automatically
- Runs compiled binary against test cases
- Students see their grade/feedback
- Professor dashboard shows all student results

### Validated (Shipped)
None yet.

### Active (In Progress)
None yet.

### Planned (Next)
- To be defined during /paul:plan

### Out of Scope
- To be defined during /paul:plan

## Constraints

### Technical Constraints
- System only active during assignment window (max 24-48h per assignment)
- Student code runs in sandboxed environment (concurrent C/C++ — safety critical)
- Deployment: local initially; Railway or Render for free prototype hosting

### Business Constraints
- Semester ends August 2026 — hard deadline for all assignments
- First assignment test: 2026-06-04
- Students identify via GitHub repo submission (no SSO required)

## Key Decisions

| Decision | Rationale | Date | Status |
|----------|-----------|------|--------|
| Django + Python backend | Already in use in codebase | 2026-06-03 | Active |
| GitHub repo submission model | Students already use GitHub; no file upload infra needed | 2026-06-03 | Active |

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Grades all students in first assignment | 100% of submissions graded | - | Not started |
| Grading turnaround | < 5 min per submission | - | Not started |

## Tech Stack / Tools

| Layer | Technology | Notes |
|-------|------------|-------|
| Backend | Django + Python | Existing codebase |
| Frontend | Django templates | Server-rendered |
| Compilation | gcc/g++ subprocess | Runs student C/C++ code |
| VCS integration | GitHub clone via git | Students submit repo URLs |
| Deployment (local) | Local server | Primary target |
| Deployment (remote) | Railway or Render | Free tier for prototype |

---
*PROJECT.md — Updated when requirements or context change*
*Last updated: 2026-06-03*
