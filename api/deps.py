from pathlib import Path
from typing import Annotated

import bleach
import markdown as md
from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.models import User
from api.security import generate_csrf_token

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "ui" / "templates"

ALLOWED_TAGS = [
    "p", "br", "hr", "pre", "code", "blockquote",
    "ul", "ol", "li", "strong", "em", "b", "i", "u",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "thead", "tbody", "tr", "th", "td",
    "a", "img", "span", "div",
]
ALLOWED_ATTRS = {
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "title"],
    "code": ["class"],
    "span": ["class"],
    "div": ["class"],
}


def render_markdown(value: str | None) -> str:
    if not value:
        return ""
    html = md.markdown(value, extensions=["extra", "fenced_code", "tables", "nl2br"])
    cleaned = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    return bleach.linkify(cleaned)


def _csrf_context(request: Request) -> dict:
    token = request.session.get("csrf_token")
    if not token:
        token = generate_csrf_token()
        request.session["csrf_token"] = token
    return {"csrf_token": token}


def _auth_context(request: Request) -> dict:
    # Role is stored in session at login; fallback keeps admin link hidden.
    return {"is_admin": request.session.get("role") == "admin"}


templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR),
    context_processors=[_csrf_context, _auth_context],
)
templates.env.filters["markdown"] = render_markdown


class LoginRequired(Exception):
    pass


class AdminRequired(Exception):
    pass


async def current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    result = await session.execute(select(User).where(User.id == uid, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user:
        # Keep session role in sync so template context (is_admin) stays authoritative.
        if request.session.get("role") != user.role:
            request.session["role"] = user.role
    return user


async def require_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    user = await current_user(request, session)
    if not user:
        raise LoginRequired()
    return user


async def require_admin(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    user = await require_user(request, session)
    if user.role != "admin":
        raise AdminRequired()
    return user
