# Project State

## Project Reference

See: .paul/PROJECT.md (updated 2026-06-03)

**Core value:** Students get immediate feedback on concurrent programming assignments without manual grading
**Current focus:** v0.1 — Phase 1 complete, system deploy-ready

## Current Position

Milestone: v0.1 Initial Release
Phase: 1 of 1 (Deploy-Ready) — Complete
Plan: 01-01 complete
Status: Ready for next planning cycle
Last activity: 2026-06-03 — Phase 1 complete (01-01 PASS)

Progress:
- Milestone: [██████████] 100%
- Phase 1: [██████████] 100%

## Loop Position

Current loop state:
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [Loop complete — ready for next PLAN]
```

## Accumulated Context

### Decisions
- FastAPI + Python backend (not Django — confirmed from codebase)
- GitHub repo submission model (students submit URL + identification)
- Local-first deployment; Railway/Render for free prototype
- PORT env var in start.sh (works local and cloud)
- SANDBOX_MODE=unshare default (Linux prod); none for macOS dev

### Deferred Issues
None.

### Blockers/Concerns
- First live test: 2026-06-04 — run `./start.sh`, create professor account, create first assignment

## Session Continuity

Last session: 2026-06-03
Stopped at: Session paused — all work committed and pushed to GitHub
Next action: cp .env.example .env → set SECRET_KEY + SANDBOX_MODE=none → ./start.sh → create professor account
Resume file: .paul/HANDOFF-2026-06-03.md
Resume context:
- Stack is FastAPI (not Django), SQLite, HTMX — Jinja2 templates
- start.sh launches web + worker; .env.example has all vars
- Professor can submit GitHub repos on behalf of students via assignment detail page
- Assignment must have GitHub enabled; repos must be public (or GITHUB_TOKEN set)

---
*STATE.md — Updated after every significant action*
