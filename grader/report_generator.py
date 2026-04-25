"""Generate grading report and compute final score."""
import json
from typing import List, Optional

from grader.test_runner import TestResult
from grader.stress_tester import StressResult
from grader.helgrind_checker import HelgrindResult


def compute_score(
    compile_ok: bool,
    test_results: Optional[List[TestResult]],
    stress_result: Optional[StressResult],
    helgrind_result: Optional[HelgrindResult],
    grading_config: dict,
    max_score: float = 10.0,
) -> float:
    """Compute the automatic score based on grading weights."""
    weights = grading_config.get("grading", grading_config)

    compile_weight = float(weights.get("compile_weight", 1.0))
    tests_weight = float(weights.get("tests_weight", 6.0))
    stress_weight = float(weights.get("stress_weight", 1.5))
    helgrind_weight = float(weights.get("helgrind_weight", 1.0))
    llm_weight = float(weights.get("llm_weight", 0.5))

    total_weight = compile_weight + tests_weight + stress_weight + helgrind_weight
    # LLM weight is added later by the professor

    score = 0.0

    # Compilation
    if compile_ok:
        score += compile_weight

    # Tests
    if test_results:
        max_test_points = sum(t.points for t in test_results)
        earned_points = sum(t.points for t in test_results if t.passed)
        if max_test_points > 0:
            score += (earned_points / max_test_points) * tests_weight
    elif not compile_ok:
        pass  # no tests if compilation failed
    else:
        score += tests_weight  # no tests configured = full marks

    # Stress
    if stress_result:
        score += stress_result.consistency * stress_weight
    elif compile_ok:
        score += stress_weight  # no stress configured = full marks

    # Helgrind
    if helgrind_result:
        if helgrind_result.ok:
            score += helgrind_weight
    elif compile_ok:
        score += helgrind_weight  # no helgrind configured = full marks

    # Normalize to max_score
    if total_weight > 0:
        normalized = (score / total_weight) * max_score
    else:
        normalized = 0.0

    return round(normalized, 2)


def test_results_to_json(results: List[TestResult]) -> str:
    return json.dumps([
        {
            "name": r.name,
            "passed": r.passed,
            "expected": r.expected,
            "got": r.got,
            "time_ms": r.time_ms,
            "points": r.points,
            "error": r.error,
        }
        for r in results
    ], ensure_ascii=False)


def stress_result_to_json(result: StressResult) -> str:
    return json.dumps({
        "runs": result.runs,
        "passed": result.passed,
        "failed": result.failed,
        "consistency": result.consistency,
        "failures": result.failures,
    }, ensure_ascii=False)
