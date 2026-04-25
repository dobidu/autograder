"""Compile C/C++ source files using gcc."""
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import config


@dataclass
class CompileResult:
    success: bool
    output: str  # stderr from gcc
    binary_path: Optional[str] = None


def compile_c(
    source_dir: Path,
    entry_point: str = "*.c",
    output_name: str = "solution",
    flags: str = None,
) -> CompileResult:
    """Compile C source files in source_dir.

    If entry_point contains a wildcard, all matching .c files are compiled.
    Otherwise, only the named file is compiled.
    """
    if flags is None:
        flags = config.DEFAULT_COMPILE_FLAGS

    binary_path = source_dir / output_name

    # Find source files
    if "*" in entry_point:
        sources = list(source_dir.glob(entry_point))
    else:
        # Could be a single file or in a subdirectory
        sources = list(source_dir.rglob(entry_point))
        if not sources:
            sources = list(source_dir.glob("*.c"))

    if not sources:
        return CompileResult(
            success=False,
            output="Nenhum arquivo .c encontrado",
        )

    cmd = [config.GCC_PATH] + flags.split() + ["-o", str(binary_path)]
    cmd += [str(s) for s in sources]

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(source_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0:
            return CompileResult(
                success=True,
                output=proc.stderr,
                binary_path=str(binary_path),
            )
        else:
            return CompileResult(
                success=False,
                output=proc.stderr or proc.stdout,
            )
    except subprocess.TimeoutExpired:
        return CompileResult(success=False, output="Compilação excedeu timeout de 30s")
    except FileNotFoundError:
        return CompileResult(success=False, output=f"gcc não encontrado em {config.GCC_PATH}")
