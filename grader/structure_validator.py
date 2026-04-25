"""Validate submission file structure."""
import json
from pathlib import Path
from typing import List, Optional, Tuple

import config


def validate_structure(
    submission_dir: Path,
    expected_files_json: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """Check that all expected files exist in submission_dir.

    Returns (ok, error_message).
    """
    if not expected_files_json:
        return True, None

    expected = json.loads(expected_files_json)
    if not expected:
        return True, None

    # Find all files recursively
    all_files = set()
    for f in submission_dir.rglob("*"):
        if f.is_file():
            all_files.add(f.name)

    missing = [f for f in expected if f not in all_files]
    if missing:
        return False, f"Arquivos não encontrados: {', '.join(missing)}"

    return True, None


def find_source_dir(submission_dir: Path) -> Path:
    """Find the actual source directory.

    ZIP files sometimes contain a single top-level directory.
    """
    entries = [e for e in submission_dir.iterdir() if not e.name.startswith(".")]
    if len(entries) == 1 and entries[0].is_dir():
        # Single directory inside — that's probably the source
        inner_entries = list(entries[0].iterdir())
        # Check if it contains source files
        if any(f.suffix in ('.c', '.h', '.cpp', '.cc') for f in entries[0].rglob("*") if f.is_file()):
            return entries[0]
    return submission_dir
