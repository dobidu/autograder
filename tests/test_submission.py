"""Tests for submission upload and validation."""
import io
import json
import zipfile
from datetime import datetime

import pytest

from app.models import Assignment, Submission


def _make_assignment(db, professor, **kwargs):
    defaults = dict(
        title="Test Assignment",
        description="# Test",
        module=1,
        max_score=10.0,
        deadline=datetime(2026, 12, 31),
        status="published",
        expected_files='["main.c"]',
        grading_config=json.dumps({
            "compile": {"entry_point": "main.c", "binary_name": "test"},
            "compile_weight": 2, "tests_weight": 8, "stress_weight": 0,
            "helgrind_weight": 0,
            "tests": [{"name": "T1", "args": [], "timeout_sec": 5,
                       "expected_output_contains": "hello", "points": 8.0}],
        }),
        created_by=professor.id,
    )
    defaults.update(kwargs)
    a = Assignment(**defaults)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _make_zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)
    return buf


def test_upload_valid_zip(client, db, professor, student, stu_cookies):
    a = _make_assignment(db, professor)
    buf = _make_zip({"main.c": '#include <stdio.h>\nint main(){printf("hello\\n");return 0;}'})

    r = client.post(
        f"/submit/{a.id}",
        files={"file": ("sol.zip", buf, "application/zip")},
        data={"github_url": ""},
        cookies=stu_cookies,
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "/submissions/" in r.headers.get("location", "")

    sub = db.query(Submission).first()
    assert sub is not None
    assert sub.status == "pending"
    assert sub.version == 1


def test_upload_missing_expected_file(client, db, professor, student, stu_cookies):
    a = _make_assignment(db, professor)
    buf = _make_zip({"wrong.c": "int main(){}"})

    r = client.post(
        f"/submit/{a.id}",
        files={"file": ("sol.zip", buf, "application/zip")},
        data={"github_url": ""},
        cookies=stu_cookies,
    )
    assert r.status_code == 400
    assert "não encontrados" in r.text


def test_upload_non_zip(client, db, professor, student, stu_cookies):
    a = _make_assignment(db, professor)

    r = client.post(
        f"/submit/{a.id}",
        files={"file": ("sol.tar.gz", io.BytesIO(b"not a zip"), "application/gzip")},
        data={"github_url": ""},
        cookies=stu_cookies,
    )
    assert r.status_code == 400
    assert ".zip" in r.text


def test_upload_no_file_or_url(client, db, professor, student, stu_cookies):
    a = _make_assignment(db, professor)

    r = client.post(
        f"/submit/{a.id}",
        data={"github_url": ""},
        cookies=stu_cookies,
    )
    assert r.status_code == 400


def test_submission_version_increments(client, db, professor, student, stu_cookies):
    a = _make_assignment(db, professor)

    for i in range(3):
        buf = _make_zip({"main.c": f'int main(){{return {i};}}'})
        client.post(
            f"/submit/{a.id}",
            files={"file": ("sol.zip", buf, "application/zip")},
            data={"github_url": ""},
            cookies=stu_cookies,
            follow_redirects=False,
        )

    subs = db.query(Submission).order_by(Submission.version).all()
    assert len(subs) == 3
    assert [s.version for s in subs] == [1, 2, 3]


def test_submission_status_page(client, db, professor, student, stu_cookies):
    a = _make_assignment(db, professor)
    buf = _make_zip({"main.c": 'int main(){return 0;}'})
    r = client.post(
        f"/submit/{a.id}",
        files={"file": ("sol.zip", buf, "application/zip")},
        data={"github_url": ""},
        cookies=stu_cookies,
        follow_redirects=False,
    )
    sub = db.query(Submission).first()

    r = client.get(f"/submissions/{sub.id}", cookies=stu_cookies)
    assert r.status_code == 200
    assert "Pendente" in r.text
