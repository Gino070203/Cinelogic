import hashlib
from pathlib import Path
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from models.user import User

router = APIRouter()

BASE = Path(__file__).resolve().parent.parent


def _read_template(filename):
    return (BASE / "frontend" / "templates" / filename).read_text(encoding="utf-8")


@router.get("/register", response_class=HTMLResponse)
async def register_page():
    return HTMLResponse(_read_template("register.html"))


@router.post("/register")
async def register(
    username: str = Form(...),
    password: str = Form(...),
    confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    if password != confirm:
        html = _read_template("register.html")\
            .replace('required autofocus>', f'value="{username}" required autofocus>')\
            .replace('<p class="error">', '<p class="error">Las contraseñas no coinciden<br>')
        return HTMLResponse(html, status_code=400)
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        html = _read_template("register.html")\
            .replace('<p class="error">', '<p class="error">El usuario ya existe<br>')
        return HTMLResponse(html, status_code=400)
    user = User(username=username, password_hash=hashlib.sha256(password.encode()).hexdigest())
    db.add(user)
    db.commit()
    return RedirectResponse(url="/login", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=302)
    return HTMLResponse(_read_template("login.html"))


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or hashlib.sha256(password.encode()).hexdigest() != user.password_hash:
        html = _read_template("login.html")\
            .replace('<p class="error">', '<p class="error">Usuario o contraseña inválidos<br>')
        return HTMLResponse(html, status_code=400)
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
