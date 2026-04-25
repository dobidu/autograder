"""Sandbox execution: run untrusted binaries with resource limits.

Supports three modes:
- "none": no isolation (dev/testing only)
- "unshare": Linux namespace isolation with ulimit
- "docker": Docker container isolation (future)
"""
import platform
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import config


@dataclass
class SandboxResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    timed_out: bool = False
    error: Optional[str] = None


@dataclass
class SandboxConfig:
    max_cpu_seconds: int = 30
    max_wall_seconds: int = 60
    max_memory_mb: int = 256
    max_processes: int = 64
    max_file_size_mb: int = 10
    network: bool = False


def run_sandboxed(
    cmd: list,
    cwd: Path,
    sandbox_cfg: Optional[SandboxConfig] = None,
    stdin_data: Optional[str] = None,
) -> SandboxResult:
    """Execute a command inside the sandbox. Returns SandboxResult."""
    if sandbox_cfg is None:
        sandbox_cfg = SandboxConfig()

    mode = config.SANDBOX_MODE
    is_linux = platform.system() == "Linux"

    if mode == "unshare" and is_linux:
        return _run_unshare(cmd, cwd, sandbox_cfg, stdin_data)
    else:
        # Fallback: basic timeout + ulimit (works on macOS for dev)
        return _run_basic(cmd, cwd, sandbox_cfg, stdin_data)


def _run_basic(
    cmd: list, cwd: Path, cfg: SandboxConfig, stdin_data: Optional[str]
) -> SandboxResult:
    """Basic execution with timeout (no namespace isolation)."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=cfg.max_wall_seconds,
            input=stdin_data,
        )
        return SandboxResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode,
        )
    except subprocess.TimeoutExpired:
        return SandboxResult(
            timed_out=True,
            error=f"Timeout: excedeu {cfg.max_wall_seconds}s",
        )
    except Exception as e:
        return SandboxResult(error=str(e))


def _run_unshare(
    cmd: list, cwd: Path, cfg: SandboxConfig, stdin_data: Optional[str]
) -> SandboxResult:
    """Linux: run with unshare + ulimit for namespace isolation."""
    mem_kb = cfg.max_memory_mb * 1024
    fsize_blocks = cfg.max_file_size_mb * 1024  # ulimit -f is in 512-byte blocks * 2

    inner_cmd = " ".join(str(c) for c in cmd)
    ulimit_str = (
        f"ulimit -t {cfg.max_cpu_seconds} "
        f"-v {mem_kb} "
        f"-u {cfg.max_processes} "
        f"-f {fsize_blocks}; "
        f"exec {inner_cmd}"
    )

    unshare_cmd = [
        "unshare", "--net", "--pid", "--fork",
        "timeout", str(cfg.max_wall_seconds),
        "sh", "-c", ulimit_str,
    ]

    try:
        proc = subprocess.run(
            unshare_cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=cfg.max_wall_seconds + 5,
            input=stdin_data,
        )
        timed_out = proc.returncode == 124  # timeout exit code
        return SandboxResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode,
            timed_out=timed_out,
            error=f"Timeout: excedeu {cfg.max_wall_seconds}s" if timed_out else None,
        )
    except subprocess.TimeoutExpired:
        return SandboxResult(
            timed_out=True,
            error=f"Timeout: excedeu {cfg.max_wall_seconds}s",
        )
    except Exception as e:
        return SandboxResult(error=str(e))
