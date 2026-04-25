"""Tests for the grading pipeline."""
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from app.models import Assignment, Submission, GradeResult
from app.services.grader_service import grade_submission


def _make_assignment(db, professor, grading_config=None, **kwargs):
    if grading_config is None:
        grading_config = {
            "compile": {"entry_point": "main.c", "binary_name": "test"},
            "compile_weight": 2, "tests_weight": 8, "stress_weight": 0,
            "helgrind_weight": 0,
            "tests": [
                {"name": "T1", "args": [], "timeout_sec": 5,
                 "expected_output_contains": "hello", "points": 8.0}
            ],
        }
    defaults = dict(
        title="Test", description="x", module=1, max_score=10.0,
        deadline=datetime(2026, 12, 31), status="published",
        expected_files='["main.c"]',
        grading_config=json.dumps(grading_config),
        created_by=professor.id,
    )
    defaults.update(kwargs)
    a = Assignment(**defaults)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _submit_zip(client, db, assignment_id, student, stu_cookies, files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)

    client.post(
        f"/submit/{assignment_id}",
        files={"file": ("sol.zip", buf, "application/zip")},
        data={"github_url": ""},
        cookies=stu_cookies,
        follow_redirects=False,
    )
    return db.query(Submission).order_by(Submission.id.desc()).first()


def test_grade_correct_code(client, db, professor, student, stu_cookies):
    a = _make_assignment(db, professor)
    sub = _submit_zip(client, db, a.id, student, stu_cookies, {
        "main.c": '#include <stdio.h>\nint main(){printf("hello\\n");return 0;}'
    })

    result = grade_submission(db, sub.id)
    assert result is True

    db.refresh(sub)
    assert sub.status == "done"
    assert sub.grade_result.compile_ok is True
    assert sub.grade_result.score_auto == 10.0
    assert sub.grade_result.is_published is True


def test_grade_compile_failure(client, db, professor, student, stu_cookies):
    a = _make_assignment(db, professor)
    sub = _submit_zip(client, db, a.id, student, stu_cookies, {
        "main.c": "int main( { }"  # syntax error
    })

    grade_submission(db, sub.id)
    db.refresh(sub)

    assert sub.status == "done"
    assert sub.grade_result.compile_ok is False
    assert sub.grade_result.score_auto == 0.0


def test_grade_wrong_output(client, db, professor, student, stu_cookies):
    a = _make_assignment(db, professor)
    sub = _submit_zip(client, db, a.id, student, stu_cookies, {
        "main.c": '#include <stdio.h>\nint main(){printf("wrong\\n");return 0;}'
    })

    grade_submission(db, sub.id)
    db.refresh(sub)

    assert sub.status == "done"
    assert sub.grade_result.compile_ok is True
    assert sub.grade_result.score_auto == 2.0  # only compile weight
    tests = json.loads(sub.grade_result.test_results)
    assert tests[0]["passed"] is False


def test_grade_with_stress_test(client, db, professor, student, stu_cookies):
    grading_config = {
        "compile": {"entry_point": "main.c", "binary_name": "test"},
        "compile_weight": 1, "tests_weight": 4, "stress_weight": 5,
        "helgrind_weight": 0,
        "tests": [
            {"name": "T1", "args": [], "timeout_sec": 5,
             "expected_output_contains": "42", "points": 4.0}
        ],
        "stress": {
            "enabled": True,
            "runs": 5,
            "args": [],
            "expected_output_contains": "42",
            "timeout_sec": 5,
        },
    }
    a = _make_assignment(db, professor, grading_config=grading_config)
    sub = _submit_zip(client, db, a.id, student, stu_cookies, {
        "main.c": '#include <stdio.h>\nint main(){printf("42\\n");return 0;}'
    })

    grade_submission(db, sub.id)
    db.refresh(sub)

    assert sub.grade_result.compile_ok is True
    assert sub.grade_result.score_auto == 10.0

    stress = json.loads(sub.grade_result.stress_results)
    assert stress["passed"] == 5
    assert stress["failed"] == 0


def test_professor_review_and_publish(client, db, professor, student, stu_cookies, prof_cookies):
    a = _make_assignment(db, professor,
        llm_config=json.dumps({"enabled": True, "rubric": "test", "context": ""}))
    sub = _submit_zip(client, db, a.id, student, stu_cookies, {
        "main.c": '#include <stdio.h>\nint main(){printf("hello\\n");return 0;}'
    })

    grade_submission(db, sub.id)
    db.refresh(sub)

    # LLM enabled -> not auto-published
    assert sub.grade_result.is_published is False

    # Professor reviews
    r = client.post(
        f"/admin/submissions/{sub.id}/review",
        data={"score_final": "8.5", "professor_notes": "Bom trabalho", "action": "publish"},
        cookies=prof_cookies,
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.refresh(sub)
    assert sub.grade_result.is_published is True
    assert sub.grade_result.score_final == 8.5
    assert sub.grade_result.professor_notes == "Bom trabalho"
