"""Run functional tests against a compiled binary."""
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.services.sandbox import SandboxConfig, SandboxResult, run_sandboxed


@dataclass
class TestCase:
    name: str
    args: List[str]
    timeout_sec: int = 10
    expected_output_contains: Optional[str] = None
    expected_output_exact: Optional[str] = None
    expected_output_regex: Optional[str] = None
    points: float = 1.0
    input_data: Optional[str] = None


@dataclass
class TestResult:
    name: str
    passed: bool
    expected: Optional[str]
    got: str
    time_ms: int
    points: float
    error: Optional[str] = None


def run_test(binary_path: Path, test: TestCase, cwd: Path) -> TestResult:
    """Run a single test case and return the result."""
    cmd = [str(binary_path)] + test.args
    cfg = SandboxConfig(max_wall_seconds=test.timeout_sec, max_cpu_seconds=test.timeout_sec)

    start = time.monotonic()
    result = run_sandboxed(cmd, cwd, cfg, stdin_data=test.input_data)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    if result.timed_out:
        return TestResult(
            name=test.name,
            passed=False,
            expected=test.expected_output_contains or test.expected_output_exact,
            got="TIMEOUT",
            time_ms=elapsed_ms,
            points=test.points,
            error=f"Timeout ({test.timeout_sec}s)",
        )

    if result.error:
        return TestResult(
            name=test.name,
            passed=False,
            expected=test.expected_output_contains or test.expected_output_exact,
            got=result.stderr[:500] if result.stderr else str(result.error),
            time_ms=elapsed_ms,
            points=test.points,
            error=result.error,
        )

    if result.exit_code != 0:
        return TestResult(
            name=test.name,
            passed=False,
            expected=test.expected_output_contains or test.expected_output_exact,
            got=f"Exit code {result.exit_code}: {result.stderr[:300]}",
            time_ms=elapsed_ms,
            points=test.points,
            error=f"Processo terminou com código {result.exit_code}",
        )

    stdout = result.stdout.strip()
    passed = False

    if test.expected_output_contains:
        passed = test.expected_output_contains in stdout
    elif test.expected_output_exact:
        passed = stdout == test.expected_output_exact.strip()
    elif test.expected_output_regex:
        passed = bool(re.search(test.expected_output_regex, stdout))
    else:
        # No expected output defined — just check it ran without error
        passed = True

    return TestResult(
        name=test.name,
        passed=passed,
        expected=test.expected_output_contains or test.expected_output_exact or test.expected_output_regex,
        got=stdout[:500],
        time_ms=elapsed_ms,
        points=test.points,
    )


def run_all_tests(binary_path: Path, tests: List[TestCase], cwd: Path) -> List[TestResult]:
    """Run all test cases sequentially."""
    return [run_test(binary_path, t, cwd) for t in tests]


def parse_tests_from_config(grading_config: dict) -> List[TestCase]:
    """Parse test cases from the grading_config JSON."""
    tests = []
    for t in grading_config.get("tests", []):
        tests.append(TestCase(
            name=t.get("name", "Test"),
            args=t.get("args", []),
            timeout_sec=t.get("timeout_sec", 10),
            expected_output_contains=t.get("expected_output_contains"),
            expected_output_exact=t.get("expected_output_exact"),
            expected_output_regex=t.get("expected_output_regex"),
            points=t.get("points", 1.0),
            input_data=t.get("input_data"),
        ))
    return tests
