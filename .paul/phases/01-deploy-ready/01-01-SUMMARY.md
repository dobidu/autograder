---
phase: 01-deploy-ready
plan: 01
subsystem: infra
tags: [deploy, startup, env, templates]

requires: []
provides:
  - start.sh — single command launches web + worker with clean shutdown
  - .env.example — all required env vars documented
  - Template accessibility/responsive fixes committed

affects: []

tech-stack:
  added: []
  patterns:
    - "Load .env via set -a/set +a in bash startup scripts"

key-files:
  created:
    - start.sh
    - .env.example
  modified:
    - templates/base.html
    - templates/professor/*.html
    - templates/student/*.html

key-decisions:
  - "PORT env var supported in start.sh for flexibility"
  - "SANDBOX_MODE defaults to unshare in .env.example (Linux prod) — doc note for macOS dev"

patterns-established: []

duration: ~5min
completed: 2026-06-03T00:00:00Z
---

# Phase 1 Plan 01: Deploy-Ready Summary

**Startup script + env config added; system is one command away from running on any machine.**

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Single-command startup | Pass | `./start.sh` starts uvicorn + worker; Ctrl+C stops both |
| AC-2: Secrets documented | Pass | All vars from config.py in `.env.example` with descriptions |
| AC-3: Template changes committed | Pass | 9 files, commit `6e0c467` |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `start.sh` | Created | Launch web + worker, trap SIGINT/SIGTERM, kill worker on exit |
| `.env.example` | Created | Document SECRET_KEY, SANDBOX_MODE, LLM, GITHUB_TOKEN |
| `templates/base.html` | Modified | preconnect hints, defer HTMX |
| `templates/professor/*.html` (5 files) | Modified | `scope="col"` on th, responsive search/grid |
| `templates/student/*.html` (3 files) | Modified | `scope="col"` on th |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `PORT` env var in start.sh | Allows Railway/Render to inject port without editing script | Works on local and cloud free tiers |
| `SANDBOX_MODE=unshare` in .env.example | Production default; added inline comment for macOS (`none`) | Clear for new deployments |

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

**Ready:**
- System starts with `./start.sh`
- Copy `.env.example` → `.env`, set `SECRET_KEY`, run script
- Create professor account: `python scripts/create_admin.py ...`

**Concerns:**
- `SECRET_KEY` is still `CHANGE-ME-IN-PRODUCTION` until user copies `.env.example`
- `SANDBOX_MODE=unshare` requires Linux; macOS users must set `none`

**Blockers:** None

---
*Phase: 01-deploy-ready, Plan: 01*
*Completed: 2026-06-03*
