"""Grading pipeline: orchestrates compilation, testing, stress, helgrind, LLM, scoring."""
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

import config
from app.models import Assignment, GradeResult, Submission
from app.services.github_service import clone_repo
from app.services.llm_service import analyze_code, is_available as llm_available, read_source_files
from grader.compiler import compile_c, CompileResult
from grader.helgrind_checker import HelgrindResult, parse_helgrind_config, run_helgrind
from grader.report_generator import (
    compute_score,
    stress_result_to_json,
    test_results_to_json,
)
from grader.stress_tester import StressResult, parse_stress_config, run_stress_test
from grader.structure_validator import find_source_dir, validate_structure
from grader.test_runner import TestResult, parse_tests_from_config, run_all_tests

logger = logging.getLogger(__name__)


def grade_submission(db: Session, submission_id: int) -> bool:
    """Run the full grading pipeline for a submission. Returns True on success."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        logger.error(f"Submission {submission_id} not found")
        return False

    assignment = sub.assignment
    grading_config = json.loads(assignment.grading_config) if assignment.grading_config else {}

    # --- 0. PREPARE SOURCE (GitHub clone if needed) ---
    source_dir = _prepare_source(db, sub, assignment)
    if source_dir is None:
        return False  # error already set

    # Find actual source root (handles ZIP with single top directory)
    source_dir = find_source_dir(source_dir)

    # --- 1. STRUCTURE VALIDATION ---
    ok, err = validate_structure(source_dir, assignment.expected_files)
    if not ok:
        _set_error(db, sub, err)
        return False

    # --- 2. COMPILATION ---
    sub.status = "compiling"
    db.commit()

    compile_cfg = grading_config.get("compile", {})
    entry_point = compile_cfg.get("entry_point", "*.c")
    binary_name = compile_cfg.get("binary_name", "solution")
    flags = assignment.compile_flags or compile_cfg.get("flags")

    compile_result = compile_c(source_dir, entry_point, binary_name, flags)

    # Initialize grade result
    grade = GradeResult(
        submission_id=sub.id,
        compile_ok=compile_result.success,
        compile_output=compile_result.output[:5000] if compile_result.output else None,
    )
    db.add(grade)
    db.commit()

    if not compile_result.success:
        grade.score_auto = 0.0
        grade.graded_at = datetime.now(timezone.utc)
        grade.is_published = True  # compilation failures are auto-published
        sub.status = "done"
        db.commit()
        return True

    binary_path = Path(compile_result.binary_path)

    # --- 3. FUNCTIONAL TESTS ---
    sub.status = "testing"
    db.commit()

    test_cases = parse_tests_from_config(grading_config)
    test_results = None
    if test_cases:
        test_results = run_all_tests(binary_path, test_cases, source_dir)
        grade.test_results = test_results_to_json(test_results)
        db.commit()

    # --- 4. STRESS TEST ---
    stress_cfg = parse_stress_config(grading_config)
    stress_result = None
    if stress_cfg:
        stress_result = run_stress_test(binary_path, stress_cfg, source_dir)
        grade.stress_results = stress_result_to_json(stress_result)
        db.commit()

    # --- 5. HELGRIND ---
    helgrind_cfg = parse_helgrind_config(grading_config)
    helgrind_result = None
    if helgrind_cfg:
        helgrind_result = run_helgrind(binary_path, helgrind_cfg, source_dir)
        grade.helgrind_ok = helgrind_result.ok
        grade.helgrind_output = helgrind_result.output
        db.commit()

    # --- 6. LLM ANALYSIS (if enabled and available) ---
    llm_config = json.loads(assignment.llm_config) if assignment.llm_config else {}
    llm_enabled = llm_config.get("enabled", False)

    if llm_enabled and llm_available():
        sub.status = "grading"
        db.commit()

        code = read_source_files(source_dir)
        rubric = llm_config.get("rubric", "Avalie a qualidade geral do código.")
        context = llm_config.get("context", "")

        llm_score, llm_feedback, raw = analyze_code(code, rubric, context)
        grade.score_llm = llm_score
        grade.llm_feedback = llm_feedback
        db.commit()
        logger.info(f"Submission {sub.id} LLM score={llm_score}")

    # --- 7. COMPUTE SCORE ---
    sub.status = "grading"
    db.commit()

    score = compute_score(
        compile_ok=True,
        test_results=test_results,
        stress_result=stress_result,
        helgrind_result=helgrind_result,
        grading_config=grading_config,
        max_score=assignment.max_score,
    )

    grade.score_auto = score
    grade.graded_at = datetime.now(timezone.utc)

    # If LLM is enabled, require professor review before publishing
    if llm_enabled:
        grade.is_published = False
    else:
        grade.score_final = score
        grade.is_published = True

    sub.status = "done"
    db.commit()

    logger.info(f"Submission {sub.id} graded: score={score}/{assignment.max_score}")
    return True


def _prepare_source(db: Session, sub: Submission, assignment: Assignment) -> Optional[Path]:
    """Prepare source directory: use file_path for uploads, clone for GitHub.

    Returns source_dir or None if error (error is set on the submission).
    """
    if sub.source == "github":
        if not sub.github_url:
            _set_error(db, sub, "URL do GitHub não informada")
            return None

        from app.services.submission_service import get_submission_dir
        dest_dir = get_submission_dir(assignment.id, sub.student_id, sub.version)
        branch = assignment.github_branch or "main"

        success, sha, err = clone_repo(
            sub.github_url,
            dest_dir,
            branch=branch,
            deadline=assignment.deadline,
        )
        if not success:
            _set_error(db, sub, f"Erro ao clonar repositório: {err}")
            return None

        sub.github_commit = sha
        sub.file_path = str(dest_dir)
        db.commit()
        return dest_dir

    # Upload: use existing file_path
    source_dir = Path(sub.file_path) if sub.file_path else None
    if not source_dir or not source_dir.exists():
        _set_error(db, sub, "Diretório de submissão não encontrado")
        return None
    return source_dir


def _set_error(db: Session, sub: Submission, error_msg: str):
    """Mark submission as error with a grade result."""
    sub.status = "error"
    grade = GradeResult(
        submission_id=sub.id,
        compile_ok=False,
        compile_output=error_msg,
        score_auto=0.0,
        graded_at=datetime.now(timezone.utc),
        is_published=True,
    )
    db.add(grade)
    db.commit()
