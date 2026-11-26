import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.deps import current_user, require_user, templates
from api.models import User
from api.security import generate_csrf_token, validate_csrf_token, verify_password

logger = logging.getLogger(__name__)

router = APIRouter()


def _ensure_csrf(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = generate_csrf_token()
        request.session["csrf_token"] = token
    return token


@router.get("/login")
async def login_page(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    csrf_token = _ensure_csrf(request)
    try:
        user = await current_user(request, session)
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        logger.warning("Login page DB check failed: %s", exc)
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "error": "Сервис временно недоступен: база данных не отвечает. Попробуйте позже.",
            },
            status_code=503,
        )
    if user:
        return RedirectResponse(url="/profile", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "csrf_token": csrf_token, "error": None},
    )


@router.post("/login")
async def login_submit(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    login: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    csrf_token: Annotated[str, Form()] = "",
):
    session_token = request.session.get("csrf_token")
    if not validate_csrf_token(session_token, csrf_token):
        new_csrf = generate_csrf_token()
        request.session["csrf_token"] = new_csrf
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "csrf_token": new_csrf, "error": "Неверный CSRF-токен."},
            status_code=400,
        )

    try:
        result = await session.execute(select(User).where(User.login == login.strip()))
        user = result.scalar_one_or_none()
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        logger.warning("Login DB query failed: %s", exc)
        new_csrf = generate_csrf_token()
        request.session["csrf_token"] = new_csrf
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "csrf_token": new_csrf,
                "error": "Сервис временно недоступен: база данных не отвечает. Попробуйте позже.",
            },
            status_code=503,
        )

    if not user or not user.is_active or not verify_password(password, user.salt, user.pwd_hash):
        new_csrf = generate_csrf_token()
        request.session["csrf_token"] = new_csrf
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "csrf_token": new_csrf, "error": "Неверный логин или пароль."},
            status_code=401,
        )

    request.session.clear()
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    request.session["csrf_token"] = generate_csrf_token()
    return RedirectResponse(url="/profile", status_code=303)


@router.post("/logout")
async def logout(request: Request, csrf_token: Annotated[str, Form()] = ""):
    session_token = request.session.get("csrf_token")
    if not validate_csrf_token(session_token, csrf_token):
        return RedirectResponse(url="/", status_code=303)
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@router.get("/profile")
async def profile(request: Request, user: Annotated[User, Depends(require_user)]):
    csrf_token = _ensure_csrf(request)
    return templates.TemplateResponse(
        request,
        "profile.html",
        {"request": request, "user": user, "csrf_token": csrf_token},
    )
