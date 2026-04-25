"""Stress testing: run binary N times and check consistency."""
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.services.sandbox import SandboxConfig, run_sandboxed


@dataclass
class StressConfig:
    runs: int = 20
    args: List[str] = None
    expected_output_contains: Optional[str] = None
    timeout_sec: int = 30
    consistency_threshold: float = 1.0  # fraction that must match

    def __post_init__(self):
        if self.args is None:
            self.args = []


@dataclass
class StressResult:
    runs: int
    passed: int
    failed: int
    consistency: float  # passed / runs
    failures: List[str]  # first few failure details


def run_stress_test(binary_path: Path, cfg: StressConfig, cwd: Path) -> StressResult:
    """Run the binary N times and verify consistent results."""
    sandbox_cfg = SandboxConfig(max_wall_seconds=cfg.timeout_sec, max_cpu_seconds=cfg.timeout_sec)
    cmd = [str(binary_path)] + cfg.args

    passed = 0
    failed = 0
    failures = []
    reference_output = None

    for i in range(cfg.runs):
        result = run_sandboxed(cmd, cwd, sandbox_cfg)

        if result.timed_out or result.error or result.exit_code != 0:
            failed += 1
            detail = f"Run {i+1}: "
            if result.timed_out:
                detail += "TIMEOUT"
            elif result.error:
                detail += result.error[:100]
            else:
                detail += f"exit={result.exit_code}"
            if len(failures) < 5:
                failures.append(detail)
            continue

        stdout = result.stdout.strip()

        if cfg.expected_output_contains:
            if cfg.expected_output_contains in stdout:
                passed += 1
            else:
                failed += 1
                if len(failures) < 5:
                    failures.append(f"Run {i+1}: got '{stdout[:100]}'")
        else:
            # Consistency check: all outputs must match
            if reference_output is None:
                reference_output = stdout
                passed += 1
            elif stdout == reference_output:
                passed += 1
            else:
                failed += 1
                if len(failures) < 5:
                    failures.append(f"Run {i+1}: output differs from run 1")

    total = passed + failed
    consistency = passed / total if total > 0 else 0.0

    return StressResult(
        runs=total,
        passed=passed,
        failed=failed,
        consistency=consistency,
        failures=failures,
    )


def parse_stress_config(grading_config: dict) -> Optional[StressConfig]:
    """Parse stress test config from grading_config JSON."""
    stress = grading_config.get("stress")
    if not stress or not stress.get("enabled", False):
        return None
    return StressConfig(
        runs=stress.get("runs", 20),
        args=stress.get("args", []),
        expected_output_contains=stress.get("expected_output_contains"),
        timeout_sec=stress.get("timeout_sec", 30),
        consistency_threshold=stress.get("consistency_threshold", 1.0),
    )
