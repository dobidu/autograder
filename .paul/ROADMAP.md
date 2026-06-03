# Roadmap: autograder

## Overview

Build a web autograder for concurrent C/C++ programming assignments: student GitHub repo submission → compile → test → grade → professor dashboard. Semester deadline August 2026; first live test 2026-06-04.

## Current Milestone

**v0.1 Initial Release** (v0.1.0)
Status: In progress
Phases: 1 of 1 complete

## Phases

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 1 | Deploy-Ready | 1 | Complete | 2026-06-03 |

## Phase Details

### Phase 1: Deploy-Ready

**Goal:** System runnable in one command with proper secrets config — ready to use for first assignment
**Depends on:** Nothing (system already functional)
**Research:** Unlikely (internal patterns only)

**Scope:**
- `start.sh` — single command launches web + worker
- `.env.example` — documents all required env vars
- Uncommitted template changes committed

**Plans:**
- [x] 01-01: startup script + env config + commit template changes

---
*Roadmap created: 2026-06-03*
*Last updated: 2026-06-03*
