#!/usr/bin/env bash
set -euo pipefail

# Load .env if present
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

echo "=============================="
echo "  LPII AutoGrader"
echo "=============================="
echo "  Web:    http://0.0.0.0:${PORT:-8000}"
echo "  Worker: grader/worker.py"
echo "  Press Ctrl+C to stop both"
echo "=============================="

# Start worker in background
python grader/worker.py &
WORKER_PID=$!

cleanup() {
    echo ""
    echo "Shutting down..."
    kill "$WORKER_PID" 2>/dev/null || true
    wait "$WORKER_PID" 2>/dev/null || true
    echo "Done."
}
trap cleanup INT TERM

# Start web server in foreground (blocking)
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"

# If uvicorn exits cleanly, also stop worker
cleanup
