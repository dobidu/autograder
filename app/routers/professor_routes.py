import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.auth import require_professor
from app.database import get_db
from app.flash import set_flash
from app.models import Assignment, GradeResult, Submission, User
from app.services.submission_service import create_submission_from_github
from app.templating import render

router = APIRouter(prefix="/admin")


@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    assignments = (
        db.query(Assignment)
        .filter(Assignment.created_by == user.id)
        .order_by(Assignment.created_at.desc())
        .all()
    )
    pending_count = db.query(Submission).filter(Submission.status == "pending").count()
    total_students = db.query(User).filter(User.role == "student", User.is_active.is_(True)).count()

    return render("professor/dashboard.html", request, {
        "user": user,
        "assignments": assignments,
        "pending_count": pending_count,
        "total_students": total_students,
    })


@router.get("/assignments/new", response_class=HTMLResponse)
def new_assignment_form(request: Request, user: User = Depends(require_professor)):
    return render("professor/assignment_form.html", request, {
        "user": user, "assignment": None, "expected_files_display": "",
        "grading_config": {}, "llm_config": {},
    })


@router.post("/assignments/new")
def create_assignment(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    module: int = Form(1),
    max_score: float = Form(10.0),
    deadline: str = Form(...),
    status: str = Form("draft"),
    compile_flags: str = Form("-Wall -Wextra -pthread"),
    expected_files: str = Form(""),
    github_enabled: bool = Form(False),
    # Grading config fields
    entry_point: str = Form("*.c"),
    binary_name: str = Form("solution"),
    compile_weight: float = Form(1.0),
    tests_weight: float = Form(6.0),
    stress_weight: float = Form(1.5),
    helgrind_weight: float = Form(1.0),
    llm_weight: float = Form(0.5),
    tests_json: str = Form("[]"),
    stress_enabled: bool = Form(False),
    stress_runs: int = Form(20),
    stress_args: str = Form(""),
    stress_expected: str = Form(""),
    stress_timeout: int = Form(30),
    helgrind_enabled: bool = Form(False),
    helgrind_args: str = Form(""),
    helgrind_timeout: int = Form(60),
    helgrind_max_errors: int = Form(0),
    llm_enabled: bool = Form(False),
    llm_rubric: str = Form(""),
    llm_context: str = Form(""),
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    files_list = [f.strip() for f in expected_files.split(",") if f.strip()] if expected_files else []

    grading_config = _build_grading_config(
        entry_point, binary_name, compile_weight, tests_weight, stress_weight,
        helgrind_weight, llm_weight, tests_json, stress_enabled, stress_runs,
        stress_args, stress_expected, stress_timeout, helgrind_enabled,
        helgrind_args, helgrind_timeout, helgrind_max_errors,
    )
    llm_config = {"enabled": llm_enabled, "rubric": llm_rubric, "context": llm_context} if llm_enabled else {}

    assignment = Assignment(
        title=title,
        description=description,
        module=module,
        max_score=max_score,
        deadline=datetime.fromisoformat(deadline),
        status=status,
        compile_flags=compile_flags,
        expected_files=json.dumps(files_list) if files_list else None,
        github_enabled=github_enabled,
        grading_config=json.dumps(grading_config) if grading_config else None,
        llm_config=json.dumps(llm_config) if llm_config else None,
        created_by=user.id,
    )
    db.add(assignment)
    db.commit()
    response = RedirectResponse(f"/admin/assignments/{assignment.id}", status_code=303)
    set_flash(response, f"Trabalho \"{title}\" criado com sucesso.")
    return response


@router.get("/assignments/{assignment_id}", response_class=HTMLResponse)
def assignment_detail(
    assignment_id: int,
    request: Request,
    q: str = Query("", alias="q"),
    status_filter: str = Query("", alias="status"),
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        return RedirectResponse("/admin/dashboard", status_code=303)

    query = db.query(Submission).filter(Submission.assignment_id == assignment_id)

    # Filter by status
    if status_filter:
        query = query.filter(Submission.status == status_filter)

    submissions = query.order_by(Submission.submitted_at.desc()).all()

    # Filter by student name (in Python since we need the relationship)
    if q:
        q_lower = q.lower()
        submissions = [s for s in submissions if q_lower in s.student.name.lower() or q_lower in (s.student.matricula or "").lower()]

    # Count by status for filter tabs
    all_count = db.query(Submission).filter(Submission.assignment_id == assignment_id).count()
    status_counts = {}
    for st in ["pending", "done", "error"]:
        status_counts[st] = db.query(Submission).filter(
            Submission.assignment_id == assignment_id, Submission.status == st
        ).count()

    return render("professor/assignment_detail.html", request, {
        "user": user,
        "assignment": assignment,
        "submissions": submissions,
        "q": q,
        "status_filter": status_filter,
        "all_count": all_count,
        "status_counts": status_counts,
    })


@router.get("/assignments/{assignment_id}/edit", response_class=HTMLResponse)
def edit_assignment_form(
    assignment_id: int,
    request: Request,
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        return RedirectResponse("/admin/dashboard", status_code=303)

    expected_files_display = ""
    if assignment.expected_files:
        try:
            expected_files_display = ", ".join(json.loads(assignment.expected_files))
        except (json.JSONDecodeError, TypeError):
            pass

    grading_config = json.loads(assignment.grading_config) if assignment.grading_config else {}
    llm_config = json.loads(assignment.llm_config) if assignment.llm_config else {}

    return render("professor/assignment_form.html", request, {
        "user": user,
        "assignment": assignment,
        "expected_files_display": expected_files_display,
        "grading_config": grading_config,
        "llm_config": llm_config,
    })


@router.post("/assignments/{assignment_id}/edit")
def update_assignment(
    assignment_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    module: int = Form(1),
    max_score: float = Form(10.0),
    deadline: str = Form(...),
    status: str = Form("draft"),
    compile_flags: str = Form("-Wall -Wextra -pthread"),
    expected_files: str = Form(""),
    github_enabled: bool = Form(False),
    entry_point: str = Form("*.c"),
    binary_name: str = Form("solution"),
    compile_weight: float = Form(1.0),
    tests_weight: float = Form(6.0),
    stress_weight: float = Form(1.5),
    helgrind_weight: float = Form(1.0),
    llm_weight: float = Form(0.5),
    tests_json: str = Form("[]"),
    stress_enabled: bool = Form(False),
    stress_runs: int = Form(20),
    stress_args: str = Form(""),
    stress_expected: str = Form(""),
    stress_timeout: int = Form(30),
    helgrind_enabled: bool = Form(False),
    helgrind_args: str = Form(""),
    helgrind_timeout: int = Form(60),
    helgrind_max_errors: int = Form(0),
    llm_enabled: bool = Form(False),
    llm_rubric: str = Form(""),
    llm_context: str = Form(""),
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        return RedirectResponse("/admin/dashboard", status_code=303)

    files_list = [f.strip() for f in expected_files.split(",") if f.strip()] if expected_files else []
    grading_config = _build_grading_config(
        entry_point, binary_name, compile_weight, tests_weight, stress_weight,
        helgrind_weight, llm_weight, tests_json, stress_enabled, stress_runs,
        stress_args, stress_expected, stress_timeout, helgrind_enabled,
        helgrind_args, helgrind_timeout, helgrind_max_errors,
    )
    llm_config = {"enabled": llm_enabled, "rubric": llm_rubric, "context": llm_context} if llm_enabled else {}

    assignment.title = title
    assignment.description = description
    assignment.module = module
    assignment.max_score = max_score
    assignment.deadline = datetime.fromisoformat(deadline)
    assignment.status = status
    assignment.compile_flags = compile_flags
    assignment.expected_files = json.dumps(files_list) if files_list else None
    assignment.github_enabled = github_enabled
    assignment.grading_config = json.dumps(grading_config) if grading_config else None
    assignment.llm_config = json.dumps(llm_config) if llm_config else None
    db.commit()

    response = RedirectResponse(f"/admin/assignments/{assignment.id}", status_code=303)
    set_flash(response, "Trabalho atualizado com sucesso.")
    return response


@router.get("/submissions/{submission_id}", response_class=HTMLResponse)
def submission_review(
    submission_id: int,
    request: Request,
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        return RedirectResponse("/admin/dashboard", status_code=303)
    return render("professor/submission_review.html", request, {
        "user": user,
        "submission": sub,
        "assignment": sub.assignment,
        "grade": sub.grade_result,
    })


@router.post("/submissions/{submission_id}/review")
def save_review(
    submission_id: int,
    score_final: float = Form(...),
    professor_notes: str = Form(""),
    action: str = Form("save"),
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub or not sub.grade_result:
        return RedirectResponse("/admin/dashboard", status_code=303)

    grade = sub.grade_result
    grade.score_final = score_final
    grade.professor_notes = professor_notes or None
    grade.reviewed_by = user.id

    if action == "publish":
        grade.is_published = True
        grade.published_at = datetime.now(timezone.utc)

    db.commit()

    response = RedirectResponse(f"/admin/submissions/{submission_id}", status_code=303)
    if action == "publish":
        set_flash(response, f"Nota {score_final} publicada para {sub.student.name}.")
    else:
        set_flash(response, "Rascunho salvo.")
    return response


@router.get("/grades", response_class=HTMLResponse)
def grades_overview(
    request: Request,
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    students = (
        db.query(User)
        .filter(User.role == "student", User.is_active.is_(True))
        .order_by(User.name)
        .all()
    )
    assignments = (
        db.query(Assignment)
        .order_by(Assignment.module, Assignment.deadline)
        .all()
    )

    grades_matrix = {}
    for student in students:
        grades_matrix[student.id] = {}
        for a in assignments:
            sub = (
                db.query(Submission)
                .filter(Submission.assignment_id == a.id, Submission.student_id == student.id)
                .order_by(Submission.version.desc())
                .first()
            )
            grades_matrix[student.id][a.id] = sub.grade_result if sub and sub.grade_result else None

    stats = []
    for a in assignments:
        scores = []
        submitted = 0
        for student in students:
            g = grades_matrix[student.id][a.id]
            if g:
                submitted += 1
                val = g.score_final if g.score_final is not None else g.score_auto
                if val is not None:
                    scores.append(val)
        if scores:
            scores_sorted = sorted(scores)
            n = len(scores_sorted)
            median = scores_sorted[n // 2] if n % 2 else (scores_sorted[n // 2 - 1] + scores_sorted[n // 2]) / 2
            mean = sum(scores) / n
            distribution = []
            for b in range(10):
                cnt = sum(1 for s in scores if b <= s < b + 1) if b < 9 else sum(1 for s in scores if s >= 9)
                distribution.append({"label": f"{b}-{b+1}", "count": cnt, "pct": cnt / n if n else 0})
            stats.append({
                "title": a.title, "mean": mean, "median": median,
                "min": scores_sorted[0], "max": scores_sorted[-1],
                "submitted": submitted, "distribution": distribution,
            })

    return render("professor/grades_overview.html", request, {
        "user": user, "students": students, "assignments": assignments,
        "grades_matrix": grades_matrix, "stats": stats,
    })


@router.post("/assignments/{assignment_id}/publish-all")
def publish_all_grades(
    assignment_id: int,
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    subs = db.query(Submission).filter(
        Submission.assignment_id == assignment_id, Submission.status == "done",
    ).all()
    count = 0
    now = datetime.now(timezone.utc)
    for sub in subs:
        if sub.grade_result and not sub.grade_result.is_published:
            grade = sub.grade_result
            if grade.score_final is None:
                grade.score_final = grade.score_auto
            grade.is_published = True
            grade.published_at = now
            grade.reviewed_by = user.id
            count += 1
    db.commit()
    response = RedirectResponse(f"/admin/assignments/{assignment_id}", status_code=303)
    set_flash(response, f"Notas publicadas para {count} aluno(s)." if count else "Nenhuma nota pendente para publicar.")
    return response


@router.post("/assignments/{assignment_id}/regrade")
def regrade_all(
    assignment_id: int,
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    subs = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.status.in_(["done", "error"]),
    ).all()
    count = len(subs)
    for sub in subs:
        if sub.grade_result:
            db.delete(sub.grade_result)
        sub.status = "pending"
    db.commit()
    response = RedirectResponse(f"/admin/assignments/{assignment_id}", status_code=303)
    set_flash(response, f"{count} submissão(ões) re-enfileirada(s) para correção.", "warning")
    return response


@router.get("/assignments/{assignment_id}/export-csv")
def export_csv(
    assignment_id: int,
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        return RedirectResponse("/admin/dashboard", status_code=303)

    students = db.query(User).filter(User.role == "student", User.is_active.is_(True)).order_by(User.name).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Nome", "Email", "Matrícula", "Nota Auto", "Nota Final", "Status"])

    for student in students:
        sub = db.query(Submission).filter(
            Submission.assignment_id == assignment_id, Submission.student_id == student.id,
        ).order_by(Submission.version.desc()).first()
        if sub and sub.grade_result:
            g = sub.grade_result
            writer.writerow([student.name, student.email, student.matricula or "",
                             g.score_auto or "", g.score_final or "",
                             "Publicada" if g.is_published else "Pendente"])
        else:
            writer.writerow([student.name, student.email, student.matricula or "", "", "", "Não submetido"])

    output.seek(0)
    filename = f"notas_{assignment.title.replace(' ', '_')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Student CRUD ──────────────────────────────────────────────────────────────

@router.get("/students", response_class=HTMLResponse)
def students_list(
    request: Request,
    q: str = Query("", alias="q"),
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(User.role == "student")
    if q:
        q_like = f"%{q}%"
        query = query.filter(
            (User.name.ilike(q_like)) | (User.email.ilike(q_like)) | (User.matricula.ilike(q_like))
        )
    students = query.order_by(User.name).all()
    total = db.query(User).filter(User.role == "student").count()
    return render("professor/students_list.html", request, {
        "user": user, "students": students, "q": q, "total": total,
    })


@router.get("/students/new", response_class=HTMLResponse)
def new_student_form(request: Request, user: User = Depends(require_professor)):
    return render("professor/student_form.html", request, {
        "user": user, "student": None,
    })


@router.post("/students/new")
def create_student(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    matricula: str = Form(""),
    is_active: bool = Form(True),
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    from app.security import hash_password

    if db.query(User).filter(User.email == email).first():
        return render("professor/student_form.html", request, {
            "user": user, "student": None,
            "error": f"Email {email} já cadastrado.",
            "form_name": name, "form_email": email, "form_matricula": matricula,
        }, status_code=400)

    if len(password) < 6:
        return render("professor/student_form.html", request, {
            "user": user, "student": None,
            "error": "Senha deve ter pelo menos 6 caracteres.",
            "form_name": name, "form_email": email, "form_matricula": matricula,
        }, status_code=400)

    student = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        matricula=matricula or None,
        role="student",
        is_active=is_active,
    )
    db.add(student)
    db.commit()
    response = RedirectResponse("/admin/students", status_code=303)
    set_flash(response, f"Aluno \"{name}\" cadastrado com sucesso.")
    return response


@router.get("/students/{student_id}/edit", response_class=HTMLResponse)
def edit_student_form(
    student_id: int,
    request: Request,
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        return RedirectResponse("/admin/students", status_code=303)
    return render("professor/student_form.html", request, {
        "user": user, "student": student,
    })


@router.post("/students/{student_id}/edit")
def update_student(
    student_id: int,
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(""),
    matricula: str = Form(""),
    is_active: bool = Form(True),
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    from app.security import hash_password

    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        return RedirectResponse("/admin/students", status_code=303)

    # Check email uniqueness (excluding current student)
    existing = db.query(User).filter(User.email == email, User.id != student_id).first()
    if existing:
        return render("professor/student_form.html", request, {
            "user": user, "student": student,
            "error": f"Email {email} já está em uso por outro usuário.",
        }, status_code=400)

    student.name = name
    student.email = email
    student.matricula = matricula or None
    student.is_active = is_active

    if password.strip():
        if len(password) < 6:
            return render("professor/student_form.html", request, {
                "user": user, "student": student,
                "error": "Senha deve ter pelo menos 6 caracteres.",
            }, status_code=400)
        student.password_hash = hash_password(password)

    db.commit()
    response = RedirectResponse("/admin/students", status_code=303)
    set_flash(response, f"Dados de \"{name}\" atualizados.")
    return response


@router.post("/students/{student_id}/delete")
def delete_student(
    student_id: int,
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        return RedirectResponse("/admin/students", status_code=303)

    name = student.name
    # Soft delete: deactivate instead of removing (preserves submission history)
    student.is_active = False
    db.commit()

    response = RedirectResponse("/admin/students", status_code=303)
    set_flash(response, f"Aluno \"{name}\" desativado.", "warning")
    return response


@router.post("/students/{student_id}/activate")
def activate_student(
    student_id: int,
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        return RedirectResponse("/admin/students", status_code=303)

    student.is_active = True
    db.commit()

    response = RedirectResponse("/admin/students", status_code=303)
    set_flash(response, f"Aluno \"{student.name}\" reativado.")
    return response


@router.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    import config as cfg
    from app.services.llm_service import is_available as llm_check

    pending_count = db.query(Submission).filter(Submission.status == "pending").count()
    processing_count = db.query(Submission).filter(
        Submission.status.in_(["compiling", "testing", "grading"])
    ).count()

    return render("professor/settings.html", request, {
        "user": user,
        "llm_available": llm_check(),
        "llm_enabled": cfg.LLM_ENABLED,
        "llm_url": cfg.LLM_BASE_URL,
        "llm_model": cfg.LLM_MODEL,
        "llm_timeout": cfg.LLM_TIMEOUT,
        "sandbox_mode": cfg.SANDBOX_MODE,
        "sandbox_timeout": cfg.SANDBOX_TIMEOUT_SEC,
        "sandbox_memory": cfg.SANDBOX_MAX_MEMORY_MB,
        "sandbox_processes": cfg.SANDBOX_MAX_PROCESSES,
        "sandbox_network": cfg.SANDBOX_NETWORK,
        "gcc_path": cfg.GCC_PATH,
        "valgrind_path": cfg.VALGRIND_PATH,
        "github_enabled": cfg.GITHUB_ENABLED,
        "max_submission_mb": cfg.MAX_SUBMISSION_SIZE_MB,
        "pending_count": pending_count,
        "processing_count": processing_count,
    })


@router.get("/assignments/{assignment_id}/submit-for-student", response_class=HTMLResponse)
def submit_for_student_form(
    assignment_id: int,
    request: Request,
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        return RedirectResponse("/admin/dashboard", status_code=303)

    students = (
        db.query(User)
        .filter(User.role == "student", User.is_active == True)
        .order_by(User.name)
        .all()
    )
    return render("professor/submit_for_student.html", request, {
        "user": user,
        "assignment": assignment,
        "students": students,
        "error": None,
    })


@router.post("/assignments/{assignment_id}/submit-for-student")
def submit_for_student(
    assignment_id: int,
    request: Request,
    student_id: int = Form(...),
    github_url: str = Form(""),
    user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        return RedirectResponse("/admin/dashboard", status_code=303)

    students = (
        db.query(User)
        .filter(User.role == "student", User.is_active == True)
        .order_by(User.name)
        .all()
    )

    def render_error(msg):
        return render("professor/submit_for_student.html", request, {
            "user": user,
            "assignment": assignment,
            "students": students,
            "error": msg,
            "selected_student_id": student_id,
            "github_url": github_url,
        })

    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        return render_error("Aluno não encontrado.")

    if not github_url.strip():
        return render_error("Informe a URL do repositório GitHub.")

    submission, err = create_submission_from_github(db, assignment, student_id, github_url.strip())
    if err:
        return render_error(err)

    response = RedirectResponse(
        f"/admin/assignments/{assignment_id}", status_code=303
    )
    set_flash(response, f"Submissão de {student.name} (v{submission.version}) enfileirada para correção.")
    return response


def _build_grading_config(
    entry_point, binary_name, compile_weight, tests_weight, stress_weight,
    helgrind_weight, llm_weight, tests_json, stress_enabled, stress_runs,
    stress_args, stress_expected, stress_timeout, helgrind_enabled,
    helgrind_args, helgrind_timeout, helgrind_max_errors,
):
    """Build grading_config dict from form fields."""
    try:
        tests = json.loads(tests_json) if tests_json else []
    except json.JSONDecodeError:
        tests = []

    config = {
        "compile": {
            "entry_point": entry_point or "*.c",
            "binary_name": binary_name or "solution",
        },
        "compile_weight": compile_weight,
        "tests_weight": tests_weight,
        "stress_weight": stress_weight,
        "helgrind_weight": helgrind_weight,
        "llm_weight": llm_weight,
        "tests": tests,
    }

    if stress_enabled:
        args = [a.strip() for a in stress_args.split() if a.strip()] if stress_args else []
        config["stress"] = {
            "enabled": True,
            "runs": stress_runs,
            "args": args,
            "expected_output_contains": stress_expected or None,
            "timeout_sec": stress_timeout,
        }

    if helgrind_enabled:
        args = [a.strip() for a in helgrind_args.split() if a.strip()] if helgrind_args else []
        config["helgrind"] = {
            "enabled": True,
            "args": args,
            "timeout_sec": helgrind_timeout,
            "max_errors": helgrind_max_errors,
        }

    return config
