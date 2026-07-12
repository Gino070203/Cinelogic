import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path

from api.routes import router as chat_router
from api.auth import router as auth_router
from api.favorites_api import router as favorites_router
from database import engine, Base
from models.user import User
from models.favorite import Favorite

BASE = Path(__file__).resolve().parent.parent

app = FastAPI(title="CineLogic")

app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "cinalogic-dev-key"))

app.mount("/static", StaticFiles(directory=str(BASE / "frontend" / "static")), name="static")

app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(favorites_router)

Base.metadata.create_all(bind=engine)
