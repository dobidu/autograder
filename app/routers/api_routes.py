from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_user
from app.database import get_db
from app.models import Submission, User

router = APIRouter(prefix="/api")


@router.get("/submissions/{submission_id}/status")
def submission_status(
    submission_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        return {"error": "not_found"}
    if user.role == "student" and sub.student_id != user.id:
        return {"error": "forbidden"}
    result = {"id": sub.id, "status": sub.status, "version": sub.version}
    if sub.grade_result and sub.grade_result.is_published:
        result["score"] = sub.grade_result.score_final
    return result
