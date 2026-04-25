import json
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy.orm import Session

import config
from app.models import Assignment, Submission
from app.utils.file_utils import safe_extract_zip

# Rate limit: minimum seconds between submissions from the same student to the same assignment
RATE_LIMIT_SECONDS = int(os.environ.get("SUBMISSION_RATE_LIMIT", "30"))


def get_submission_dir(assignment_id: int, student_id: int, version: int) -> Path:
    return config.SUBMISSIONS_DIR / str(assignment_id) / str(student_id) / str(version)


def count_submissions(db: Session, assignment_id: int, student_id: int) -> int:
    return (
        db.query(Submission)
        .filter(
            Submission.assignment_id == assignment_id,
            Submission.student_id == student_id,
        )
        .count()
    )


def validate_submission_allowed(
    db: Session, assignment: Assignment, student_id: int
) -> Optional[str]:
    """Return error message if submission is not allowed, None if OK."""
    now = datetime.now(timezone.utc)
    deadline = assignment.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if deadline <= now and not assignment.allow_late:
        return "Prazo encerrado para este trabalho"

    if assignment.status != "published":
        return "Este trabalho não está aberto para submissões"

    if assignment.max_submissions > 0:
        count = count_submissions(db, assignment.id, student_id)
        if count >= assignment.max_submissions:
            return "Limite de submissões atingido ({})".format(assignment.max_submissions)

    # Rate limiting: check last submission time for this student on this assignment
    last_sub = (
        db.query(Submission)
        .filter(
            Submission.student_id == student_id,
            Submission.assignment_id == assignment.id,
        )
        .order_by(Submission.submitted_at.desc())
        .first()
    )
    if last_sub and last_sub.submitted_at:
        last_time = last_sub.submitted_at
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        elapsed = (now - last_time).total_seconds()
        if elapsed < RATE_LIMIT_SECONDS:
            wait = int(RATE_LIMIT_SECONDS - elapsed)
            return "Aguarde {} segundo(s) antes de enviar outra submissão".format(wait)

    return None


def validate_structure(extracted_files: list, assignment: Assignment) -> Optional[str]:
    """Check that expected files are present. Return error or None."""
    if not assignment.expected_files:
        return None

    expected = json.loads(assignment.expected_files)
    if not expected:
        return None

    basenames = {Path(f).name for f in extracted_files}
    missing = [f for f in expected if f not in basenames]
    if missing:
        return "Arquivos obrigatórios não encontrados: {}".format(", ".join(missing))
    return None


def create_submission_from_upload(
    db: Session,
    assignment: Assignment,
    student_id: int,
    zip_path: Path,
) -> Tuple[Optional[Submission], Optional[str]]:
    """Process a ZIP upload. Returns (submission, error_message)."""
    version = count_submissions(db, assignment.id, student_id) + 1
    dest_dir = get_submission_dir(assignment.id, student_id, version)
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        extracted = safe_extract_zip(zip_path, dest_dir)
    except ValueError as e:
        shutil.rmtree(dest_dir, ignore_errors=True)
        return None, str(e)

    if not extracted:
        shutil.rmtree(dest_dir, ignore_errors=True)
        return None, "Arquivo ZIP vazio"

    err = validate_structure(extracted, assignment)
    if err:
        shutil.rmtree(dest_dir, ignore_errors=True)
        return None, err

    submission = Submission(
        assignment_id=assignment.id,
        student_id=student_id,
        source="upload",
        file_path=str(dest_dir),
        version=version,
        status="pending",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return submission, None


def create_submission_from_github(
    db: Session,
    assignment: Assignment,
    student_id: int,
    github_url: str,
) -> Tuple[Optional[Submission], Optional[str]]:
    """Create a submission for a GitHub repo. Validates URL and accessibility first."""
    if not assignment.github_enabled:
        return None, "Submissão via GitHub não habilitada para este trabalho"

    # Validate URL format
    from app.services.github_service import validate_github_url, check_repo_accessible

    ok, err = validate_github_url(github_url)
    if not ok:
        return None, err

    # Check repo is accessible before creating submission
    ok, err = check_repo_accessible(github_url)
    if not ok:
        return None, "Repositório não acessível: {}".format(err)

    version = count_submissions(db, assignment.id, student_id) + 1

    submission = Submission(
        assignment_id=assignment.id,
        student_id=student_id,
        source="github",
        github_url=github_url,
        version=version,
        status="pending",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return submission, None
