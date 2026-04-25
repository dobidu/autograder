"""GitHub integration: clone repos and checkout by deadline."""
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import config

logger = logging.getLogger(__name__)


def validate_github_url(url: str) -> Tuple[bool, Optional[str]]:
    """Basic validation of a GitHub URL. Returns (ok, error)."""
    url = url.strip()
    if not url:
        return False, "URL vazia"
    if not (url.startswith("https://github.com/") or url.startswith("git@github.com:")):
        return False, "URL deve ser do GitHub (https://github.com/...)"
    # Reject URLs with suspicious characters
    if any(c in url for c in [";", "&", "|", "`", "$", "(", ")"]):
        return False, "URL contém caracteres inválidos"
    return True, None


def clone_repo(
    github_url: str,
    dest_dir: Path,
    branch: str = "main",
    deadline: Optional[datetime] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Clone a GitHub repo and optionally checkout to the last commit before deadline.

    Returns (success, commit_sha, error_message).
    """
    ok, err = validate_github_url(github_url)
    if not ok:
        return False, None, err

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Build clone URL with optional token
    clone_url = github_url
    if config.GITHUB_ACCESS_TOKEN and clone_url.startswith("https://"):
        # Insert token for private repos
        clone_url = clone_url.replace(
            "https://github.com/",
            f"https://{config.GITHUB_ACCESS_TOKEN}@github.com/",
        )

    # Clone
    try:
        proc = subprocess.run(
            [
                "git", "clone",
                "--depth", "100",  # enough history to find deadline commit
                "--branch", branch,
                "--single-branch",
                clone_url,
                str(dest_dir),
            ],
            capture_output=True,
            text=True,
            timeout=config.GITHUB_CLONE_TIMEOUT,
        )
        if proc.returncode != 0:
            return False, None, f"git clone falhou: {proc.stderr[:500]}"
    except subprocess.TimeoutExpired:
        return False, None, f"git clone timeout ({config.GITHUB_CLONE_TIMEOUT}s)"
    except FileNotFoundError:
        return False, None, "git não encontrado no sistema"

    # If deadline specified, find the last commit before it
    commit_sha = None
    if deadline:
        commit_sha, err = _checkout_before_deadline(dest_dir, deadline)
        if err:
            return False, None, err
    else:
        # Get HEAD sha
        commit_sha = _get_head_sha(dest_dir)

    return True, commit_sha, None


def _checkout_before_deadline(repo_dir: Path, deadline: datetime) -> Tuple[Optional[str], Optional[str]]:
    """Find and checkout the last commit before deadline.

    Returns (commit_sha, error_message).
    """
    deadline_str = deadline.strftime("%Y-%m-%dT%H:%M:%S")

    try:
        # Find last commit before deadline
        proc = subprocess.run(
            [
                "git", "log",
                f"--until={deadline_str}",
                "-1",
                "--format=%H",
            ],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
        sha = proc.stdout.strip()
        if not sha:
            return None, "Nenhum commit encontrado antes do deadline"

        # Checkout that commit
        proc = subprocess.run(
            ["git", "checkout", sha],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return None, f"git checkout falhou: {proc.stderr[:300]}"

        return sha, None
    except subprocess.TimeoutExpired:
        return None, "git log/checkout timeout"
    except Exception as e:
        return None, str(e)


def _get_head_sha(repo_dir: Path) -> Optional[str]:
    """Get the current HEAD commit SHA."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.stdout.strip() or None
    except Exception:
        return None


def check_repo_accessible(github_url: str) -> Tuple[bool, Optional[str]]:
    """Check if a GitHub repo is accessible (public or with token)."""
    ok, err = validate_github_url(github_url)
    if not ok:
        return False, err

    check_url = github_url
    if config.GITHUB_ACCESS_TOKEN and check_url.startswith("https://"):
        check_url = check_url.replace(
            "https://github.com/",
            f"https://{config.GITHUB_ACCESS_TOKEN}@github.com/",
        )

    try:
        proc = subprocess.run(
            ["git", "ls-remote", "--exit-code", check_url],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode == 0:
            return True, None
        return False, "Repositório não acessível (privado ou inexistente)"
    except subprocess.TimeoutExpired:
        return False, "Timeout ao verificar repositório"
    except FileNotFoundError:
        return False, "git não encontrado no sistema"
