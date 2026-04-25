import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_student
from app.database import get_db
from app.flash import set_flash
from app.models import Assignment, GradeResult, Submission, User
from app.services.submission_service import (
    create_submission_from_github,
    create_submission_from_upload,
    validate_submission_allowed,
)
from app.templating import render

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.role == "professor":
        return RedirectResponse("/admin/dashboard", status_code=303)

    assignments = (
        db.query(Assignment)
        .filter(Assignment.status == "published")
        .order_by(Assignment.deadline.desc())
        .all()
    )

    submission_map = {}
    for a in assignments:
        sub = (
            db.query(Submission)
            .filter(Submission.assignment_id == a.id, Submission.student_id == user.id)
            .order_by(Submission.version.desc())
            .first()
        )
        submission_map[a.id] = sub

    now = datetime.now(timezone.utc)

    def _is_past(dl):
        dl_utc = dl.replace(tzinfo=timezone.utc) if dl.tzinfo is None else dl
        return dl_utc <= now

    closed_ids = {a.id for a in assignments if _is_past(a.deadline)}

    return render("student/dashboard.html", request, {
        "user": user,
        "assignments": assignments,
        "submission_map": submission_map,
        "closed_ids": closed_ids,
        "now": now,
    })


@router.get("/assignments/{assignment_id}", response_class=HTMLResponse)
def assignment_detail(
    assignment_id: int,
    request: Request,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id, Assignment.status == "published",
    ).first()
    if not assignment:
        return RedirectResponse("/dashboard", status_code=303)

    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id, Submission.student_id == user.id)
        .order_by(Submission.version.desc())
        .all()
    )

    now = datetime.now(timezone.utc)
    dl = assignment.deadline
    if dl.tzinfo is None:
        dl = dl.replace(tzinfo=timezone.utc)
    deadline_passed = dl <= now

    return render("student/assignment_detail.html", request, {
        "user": user,
        "assignment": assignment,
        "submissions": submissions,
        "deadline_passed": deadline_passed,
        "now": now,
    })


@router.post("/submit/{assignment_id}")
def submit(
    assignment_id: int,
    request: Request,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
    file: UploadFile = File(None),
    github_url: str = Form(""),
):
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id, Assignment.status == "published",
    ).first()
    if not assignment:
        return RedirectResponse("/dashboard", status_code=303)

    error = validate_submission_allowed(db, assignment, user.id)
    if error:
        return _assignment_detail_with_error(request, user, db, assignment, error)

    submission = None

    if file and file.filename:
        if not file.filename.lower().endswith(".zip"):
            return _assignment_detail_with_error(request, user, db, assignment, "Apenas arquivos .zip são aceitos")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            content = file.file.read()
            if len(content) > 10 * 1024 * 1024:
                return _assignment_detail_with_error(request, user, db, assignment, "Arquivo excede 10MB")
            tmp.write(content)
            tmp_path = Path(tmp.name)
        submission, err = create_submission_from_upload(db, assignment, user.id, tmp_path)
        tmp_path.unlink(missing_ok=True)
    elif github_url.strip():
        submission, err = create_submission_from_github(db, assignment, user.id, github_url.strip())
    else:
        err = "Envie um arquivo ZIP ou informe a URL do repositório GitHub"

    if err:
        return _assignment_detail_with_error(request, user, db, assignment, err)

    response = RedirectResponse(f"/submissions/{submission.id}", status_code=303)
    set_flash(response, f"Submissão v{submission.version} enviada com sucesso! Seu código será corrigido automaticamente.")
    return response


def _assignment_detail_with_error(request, user, db, assignment, error):
    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment.id, Submission.student_id == user.id)
        .order_by(Submission.version.desc())
        .all()
    )
    now = datetime.now(timezone.utc)
    dl = assignment.deadline
    if dl.tzinfo is None:
        dl = dl.replace(tzinfo=timezone.utc)
    deadline_passed = dl <= now
    return render("student/assignment_detail.html", request, {
        "user": user,
        "assignment": assignment,
        "submissions": submissions,
        "deadline_passed": deadline_passed,
        "now": now,
        "error": error,
    }, status_code=400)


@router.get("/submissions/{submission_id}", response_class=HTMLResponse)
def submission_status(
    submission_id: int,
    request: Request,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    sub = db.query(Submission).filter(
        Submission.id == submission_id, Submission.student_id == user.id,
    ).first()
    if not sub:
        return RedirectResponse("/dashboard", status_code=303)

    return render("student/submission_status.html", request, {
        "user": user,
        "submission": sub,
        "assignment": sub.assignment,
        "grade": sub.grade_result,
    })


@router.get("/grades", response_class=HTMLResponse)
def grades(
    request: Request,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    assignments = (
        db.query(Assignment)
        .filter(Assignment.status.in_(["published", "closed"]))
        .order_by(Assignment.module, Assignment.deadline)
        .all()
    )

    grades_data = []
    for a in assignments:
        sub = (
            db.query(Submission)
            .filter(Submission.assignment_id == a.id, Submission.student_id == user.id)
            .order_by(Submission.version.desc())
            .first()
        )
        grade = None
        if sub and sub.grade_result and sub.grade_result.is_published:
            grade = sub.grade_result
        grades_data.append({"assignment": a, "submission": sub, "grade": grade})

    return render("student/grades.html", request, {"user": user, "grades_data": grades_data})
