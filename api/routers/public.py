import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from jinja2 import TemplateNotFound
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.db import get_session
from api.deps import current_user, render_markdown, require_admin, templates
from api.models import Article, User

router = APIRouter()

_AGENT_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _normalize_agent_slug(agent_name: str) -> str:
    slug = agent_name.strip().lower()
    if not slug or not _AGENT_SLUG_RE.fullmatch(slug):
        raise HTTPException(status_code=404, detail="Agent not found")
    return slug


@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})


@router.get("/tierlist")
async def tierlist(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    is_admin = False
    try:
        user = await current_user(request, session)
        is_admin = bool(user and user.role == "admin")
    except Exception:
        # DB unavailable: fail closed to non-admin view, keep page renderable.
        is_admin = False
    return templates.TemplateResponse(
        request,
        "tierlist.html",
        {"request": request, "is_admin": is_admin},
    )


def _serialize_article(article: Article) -> dict:
    return {
        "id": article.id,
        "title": article.title,
        "content_md": article.content or "",
        "content_html": render_markdown(article.content),
        "map": article.map.name if article.map else None,
        "side": article.side.name if article.side else None,
        "role": article.role.name if article.role else None,
        "characters": [c.name for c in (article.characters or [])],
        "created_at": article.created_at.isoformat() if article.created_at else None,
    }


async def _load_library_articles(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        select(Article)
        .options(
            selectinload(Article.map),
            selectinload(Article.side),
            selectinload(Article.role),
            selectinload(Article.characters),
        )
        .order_by(Article.created_at.desc(), Article.id.desc())
    )
    articles = result.scalars().unique().all()
    return [_serialize_article(a) for a in articles]


@router.get("/library")
async def library(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        articles = await _load_library_articles(session)
    except Exception:
        articles = []
    return templates.TemplateResponse(
        request,
        "library.html",
        {"request": request, "articles": articles},
    )


@router.get("/api/library/articles")
async def library_articles(session: Annotated[AsyncSession, Depends(get_session)]):
    articles = await _load_library_articles(session)
    return {"articles": articles}


@router.get("/coaching")
async def coaching(request: Request):
    return templates.TemplateResponse(request, "coaching.html", {"request": request})


@router.get("/about")
async def about(request: Request):
    return templates.TemplateResponse(request, "about.html", {"request": request})


@router.get("/agent/{agent_name}")
async def agent(request: Request, agent_name: str):
    agent_slug = _normalize_agent_slug(agent_name)
    return templates.TemplateResponse(
        request,
        "agent.html",
        {
            "request": request,
            "agent_name": agent_slug,
            "agent_slug": agent_slug,
        },
    )


@router.get("/admin-panel")
async def admin_panel_page(
    request: Request,
    user: Annotated[User, Depends(require_admin)],
):
    context = {
        "request": request,
        "user": user,
        "is_admin": True,
    }
    try:
        return templates.TemplateResponse(request, "admin_panel.html", context)
    except TemplateNotFound:
        return PlainTextResponse(
            "Admin panel template (ui/templates/admin_panel.html) is not created yet. "
            "Backend API is available under /api/admin/*.",
            status_code=200,
        )
