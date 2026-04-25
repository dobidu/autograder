from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import (
    clear_session_cookie,
    get_current_user,
    set_session_cookie,
)
from app.database import get_db
from app.flash import set_flash
from app.models import User
from app.security import create_session_token, hash_password, verify_password
from app.templating import render

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user=Depends(get_current_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return render("login.html", request)


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return render("login.html", request, {"error": "Email ou senha incorretos"}, status_code=400)
    if not user.is_active:
        return render("login.html", request, {"error": "Conta desativada"}, status_code=400)
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    token = create_session_token(user.id)
    response = RedirectResponse("/dashboard", status_code=303)
    set_session_cookie(response, token)
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user=Depends(get_current_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return render("register.html", request)


@router.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    matricula: str = Form(""),
    db: Session = Depends(get_db),
):
    errors = []
    if password != password_confirm:
        errors.append("Senhas não coincidem")
    if len(password) < 6:
        errors.append("Senha deve ter pelo menos 6 caracteres")
    if db.query(User).filter(User.email == email).first():
        errors.append("Email já cadastrado")
    if errors:
        return render(
            "register.html", request,
            {"error": "; ".join(errors), "name": name, "email": email, "matricula": matricula},
            status_code=400,
        )
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        matricula=matricula or None,
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_session_token(user.id)
    response = RedirectResponse("/dashboard", status_code=303)
    set_session_cookie(response, token)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    clear_session_cookie(response)
    return response
