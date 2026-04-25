from typing import Optional

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import validate_session_token

SESSION_COOKIE = "session"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    user_id = validate_session_token(token)
    if user_id is None:
        return None
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    return user


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_professor(request: Request, db: Session = Depends(get_db)) -> User:
    user = require_user(request, db)
    if user.role != "professor":
        raise HTTPException(status_code=403, detail="Acesso restrito a professores")
    return user


def require_student(request: Request, db: Session = Depends(get_db)) -> User:
    user = require_user(request, db)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Acesso restrito a alunos")
    return user


def set_session_cookie(response: Response, token: str):
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=24 * 3600,
    )


def clear_session_cookie(response: Response):
    response.delete_cookie(SESSION_COOKIE)
