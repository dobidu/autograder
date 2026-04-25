#!/usr/bin/env python3
"""Seed the database with example assignments from the examples/ directory."""
import json
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Base, engine
from app.models import Assignment, User

Base.metadata.create_all(bind=engine)

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def load_example(example_dir: Path, professor_id: int) -> dict:
    """Load an example assignment from its directory."""
    config_path = example_dir / "assignment.json"
    if not config_path.exists():
        return None

    with open(config_path) as f:
        config = json.load(f)

    # Load description from markdown file
    desc_file = config.get("description_file", "enunciado.md")
    desc_path = example_dir / desc_file
    description = desc_path.read_text() if desc_path.exists() else config.get("title", "")

    # Parse deadline
    deadline_str = config.get("deadline", "2026-12-31T23:59:00")
    try:
        deadline = datetime.fromisoformat(deadline_str)
    except ValueError:
        deadline = datetime(2026, 12, 31, 23, 59)

    compile_cfg = config.get("compile", {})
    grading = config.get("grading", {})
    llm = config.get("llm", {})
    submission = config.get("submission", {})

    # Build grading_config (merge compile info into grading)
    grading_config = dict(grading)
    grading_config["compile"] = compile_cfg

    return {
        "title": config["title"],
        "description": description,
        "module": config.get("module"),
        "max_score": config.get("max_score", 10.0),
        "deadline": deadline,
        "status": "published",
        "compile_flags": compile_cfg.get("flags", "-Wall -Wextra -pthread"),
        "expected_files": json.dumps(compile_cfg.get("expected_files", [])),
        "github_enabled": submission.get("github_enabled", False),
        "github_branch": submission.get("github_branch", "main"),
        "grading_config": json.dumps(grading_config),
        "llm_config": json.dumps(llm) if llm else None,
        "max_submissions": submission.get("max_submissions", -1),
        "scoring_mode": submission.get("scoring_mode", "last"),
        "created_by": professor_id,
    }


def main():
    db = SessionLocal()

    # Find or require a professor
    professor = db.query(User).filter(User.role == "professor").first()
    if not professor:
        print("Nenhum professor encontrado. Crie um com scripts/create_admin.py primeiro.")
        sys.exit(1)

    print(f"Usando professor: {professor.name} (id={professor.id})")

    # Load all examples
    example_dirs = sorted(EXAMPLES_DIR.iterdir())
    loaded = 0

    for edir in example_dirs:
        if not edir.is_dir():
            continue

        data = load_example(edir, professor.id)
        if not data:
            continue

        # Check if already exists
        existing = db.query(Assignment).filter(Assignment.title == data["title"]).first()
        if existing:
            print(f"  Já existe: {data['title']} (id={existing.id}), pulando.")
            continue

        assignment = Assignment(**data)
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        print(f"  Criado: {data['title']} (id={assignment.id})")
        loaded += 1

    print(f"\n{loaded} exercício(s) carregado(s).")
    db.close()


if __name__ == "__main__":
    main()
