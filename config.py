import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage")))
DB_PATH = STORAGE_DIR / "db" / "autograder.db"
SUBMISSIONS_DIR = STORAGE_DIR / "submissions"
ASSIGNMENTS_DIR = STORAGE_DIR / "assignments"

# App
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE-ME-IN-PRODUCTION")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
SITE_NAME = "LPII AutoGrader"
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")

# Auth
SESSION_EXPIRE_HOURS = 24
BCRYPT_ROUNDS = 12

# Sandbox
SANDBOX_MODE = os.getenv("SANDBOX_MODE", "unshare")  # "unshare" | "docker" | "none"
SANDBOX_TIMEOUT_SEC = 60
SANDBOX_MAX_MEMORY_MB = 256
SANDBOX_MAX_PROCESSES = 64
SANDBOX_NETWORK = False

# Compilation
DEFAULT_COMPILE_FLAGS = "-Wall -Wextra -pthread -g"
GCC_PATH = "/usr/bin/gcc"
VALGRIND_PATH = "/usr/bin/valgrind"

# LLM
LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() == "true"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5-coder:14b")
LLM_TIMEOUT = 120
LLM_MAX_CODE_LENGTH = 50000

# GitHub
GITHUB_ENABLED = True
GITHUB_ACCESS_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_CLONE_TIMEOUT = 60

# Grading
MAX_SUBMISSION_SIZE_MB = 10
MAX_FILE_SIZE_MB = 1
STRESS_DEFAULT_RUNS = 20
