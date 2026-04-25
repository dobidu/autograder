"""Background worker that polls for pending submissions and grades them.

Includes crash recovery: on startup and periodically, re-queues submissions
stuck in intermediate states (compiling/testing/grading) for longer than
STUCK_TIMEOUT_MINUTES.
"""
import logging
import signal
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Submission, GradeResult
from app.services.grader_service import grade_submission

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("grader.worker")

POLL_INTERVAL = 5  # seconds
STUCK_TIMEOUT_MINUTES = 10  # re-queue submissions stuck longer than this
RECOVERY_CHECK_INTERVAL = 60  # check for stuck submissions every N seconds
running = True


def handle_signal(signum, frame):
    global running
    logger.info("Received shutdown signal, finishing current job...")
    running = False


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def recover_stuck_submissions():
    """Find submissions stuck in intermediate states and re-queue them.

    This handles the case where the worker crashed mid-grading.
    Submissions in 'compiling', 'testing', or 'grading' that haven't
    been updated in STUCK_TIMEOUT_MINUTES are reset to 'pending'.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=STUCK_TIMEOUT_MINUTES)
        stuck = (
            db.query(Submission)
            .filter(
                Submission.status.in_(["compiling", "testing", "grading"]),
                Submission.submitted_at < cutoff,
            )
            .all()
        )
        if not stuck:
            return 0

        count = 0
        for sub in stuck:
            # Remove partial grade result if exists
            if sub.grade_result:
                db.delete(sub.grade_result)
            sub.status = "pending"
            count += 1
            logger.warning(
                f"Recovered stuck submission {sub.id} "
                f"(was '{sub.status}', student={sub.student_id}, assignment={sub.assignment_id})"
            )

        db.commit()
        if count:
            logger.info(f"Recovered {count} stuck submission(s)")
        return count
    finally:
        db.close()


def poll_and_grade():
    """Check for pending submissions and grade the oldest one."""
    db = SessionLocal()
    try:
        sub = (
            db.query(Submission)
            .filter(Submission.status == "pending")
            .order_by(Submission.submitted_at.asc())
            .first()
        )
        if not sub:
            return False

        logger.info(
            f"Grading submission {sub.id} "
            f"(assignment={sub.assignment_id}, student={sub.student_id}, v{sub.version})"
        )

        try:
            grade_submission(db, sub.id)
        except Exception as e:
            logger.exception(f"Error grading submission {sub.id}: {e}")
            sub.status = "error"
            # Store error details in a grade result
            if not sub.grade_result:
                grade = GradeResult(
                    submission_id=sub.id,
                    compile_ok=False,
                    compile_output=f"Erro interno do sistema: {str(e)[:500]}",
                    score_auto=0.0,
                    graded_at=datetime.now(timezone.utc),
                    is_published=True,
                )
                db.add(grade)
            db.commit()

        return True
    finally:
        db.close()


def main():
    logger.info("Grader worker started. Polling for submissions...")

    # Recover any stuck submissions from previous crashes
    recovered = recover_stuck_submissions()
    if recovered:
        logger.info(f"Startup recovery: {recovered} submission(s) re-queued")

    last_recovery_check = time.monotonic()

    while running:
        had_work = poll_and_grade()

        if not had_work:
            time.sleep(POLL_INTERVAL)

        # Periodic recovery check
        now = time.monotonic()
        if now - last_recovery_check >= RECOVERY_CHECK_INTERVAL:
            recover_stuck_submissions()
            last_recovery_check = now

    logger.info("Worker stopped.")


if __name__ == "__main__":
    main()
