import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.db import get_session
from api.deps import current_user
from api.models import Article, Character, Map, Role, Side, User
from api.security import validate_csrf_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin")


def _csrf_token_from_request(request: Request, body: dict | None) -> str | None:
    header_token = request.headers.get("X-CSRF-Token")
    if header_token:
        return header_token
    if isinstance(body, dict):
        body_token = body.get("csrf_token")
        if isinstance(body_token, str):
            return body_token
    return None


def _require_admin_api(user: User | None) -> JSONResponse | None:
    if not user or user.role != "admin":
        return JSONResponse({"error": "Forbidden"}, status_code=403)
    return None


def _check_csrf(request: Request, body: dict | None) -> JSONResponse | None:
    token = _csrf_token_from_request(request, body)
    if not validate_csrf_token(request.session.get("csrf_token"), token):
        return JSONResponse({"error": "Invalid CSRF token"}, status_code=403)
    return None


def _db_error_response(exc: Exception) -> JSONResponse:
    logger.warning("Admin API DB error: %s", exc)
    return JSONResponse(
        {"error": "Service temporarily unavailable: database connection failed."},
        status_code=503,
    )


def _article_to_dict(article: Article) -> dict:
    return {
        "id": article.id,
        "title": article.title,
        "content": article.content or "",
        "map_id": article.map_id,
        "map_name": article.map.name if article.map else None,
        "side_id": article.side_id,
        "side_name": article.side.name if article.side else None,
        "role_id": article.role_id,
        "role_name": article.role.name if article.role else None,
        "character_ids": [c.id for c in (article.characters or [])],
        "characters": [
            {"id": c.id, "name": c.name} for c in (article.characters or [])
        ],
        "created_at": article.created_at.isoformat() if article.created_at else None,
    }


def _character_to_dict(character: Character) -> dict:
    return {
        "id": character.id,
        "name": character.name,
        "role_id": character.role_id,
        "role_name": character.role.name if character.role else None,
        "description": character.description or "",
        "icon_url": character.icon_url or "",
    }


async def _load_article(session: AsyncSession, article_id: int) -> Article | None:
    result = await session.execute(
        select(Article)
        .options(
            selectinload(Article.map),
            selectinload(Article.side),
            selectinload(Article.role),
            selectinload(Article.characters),
        )
        .where(Article.id == article_id)
    )
    return result.scalar_one_or_none()


def _clean_optional_int(value, field: str) -> tuple[int | None, str | None]:
    if value is None or value == "":
        return None, None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, f"Field '{field}' must be an integer or null"
    if parsed <= 0:
        return None, f"Field '{field}' must be a positive integer or null"
    return parsed, None


def _parse_article_payload(body: dict) -> tuple[dict | None, str | None]:
    if not isinstance(body, dict):
        return None, "Body must be a JSON object"

    title = body.get("title")
    if not isinstance(title, str) or not title.strip():
        return None, "Field 'title' is required"
    title = title.strip()
    if len(title) > 255:
        return None, "Field 'title' must be at most 255 characters"

    content = body.get("content")
    if content is None:
        content = ""
    if not isinstance(content, str):
        return None, "Field 'content' must be a string"

    map_id, err = _clean_optional_int(body.get("map_id"), "map_id")
    if err:
        return None, err
    side_id, err = _clean_optional_int(body.get("side_id"), "side_id")
    if err:
        return None, err
    role_id, err = _clean_optional_int(body.get("role_id"), "role_id")
    if err:
        return None, err

    raw_character_ids = body.get("character_ids", [])
    if raw_character_ids is None:
        raw_character_ids = []
    if not isinstance(raw_character_ids, list):
        return None, "Field 'character_ids' must be a list of integers"
    character_ids: list[int] = []
    seen = set()
    for idx, cid in enumerate(raw_character_ids):
        try:
            parsed = int(cid)
        except (TypeError, ValueError):
            return None, f"character_ids[{idx}] must be an integer"
        if parsed <= 0:
            return None, f"character_ids[{idx}] must be a positive integer"
        if parsed not in seen:
            seen.add(parsed)
            character_ids.append(parsed)

    return {
        "title": title,
        "content": content,
        "map_id": map_id,
        "side_id": side_id,
        "role_id": role_id,
        "character_ids": character_ids,
    }, None


async def _validate_article_refs(
    session: AsyncSession, data: dict
) -> str | None:
    if data["map_id"] is not None:
        if not await session.get(Map, data["map_id"]):
            return "Map not found"
    if data["side_id"] is not None:
        if not await session.get(Side, data["side_id"]):
            return "Side not found"
    if data["role_id"] is not None:
        if not await session.get(Role, data["role_id"]):
            return "Role not found"
    if data["character_ids"]:
        result = await session.execute(
            select(Character.id).where(Character.id.in_(data["character_ids"]))
        )
        found = set(result.scalars().all())
        missing = [cid for cid in data["character_ids"] if cid not in found]
        if missing:
            return f"Characters not found: {missing}"
    return None


async def _apply_article_characters(
    session: AsyncSession, article: Article, character_ids: list[int]
) -> None:
    if not character_ids:
        article.characters = []
        return
    result = await session.execute(
        select(Character).where(Character.id.in_(character_ids))
    )
    chars_by_id = {c.id: c for c in result.scalars().all()}
    article.characters = [chars_by_id[cid] for cid in character_ids if cid in chars_by_id]


@router.get("/references")
async def get_references(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
):
    forbidden = _require_admin_api(user)
    if forbidden:
        return forbidden
    try:
        roles = (await session.execute(select(Role).order_by(Role.id))).scalars().all()
        sides = (await session.execute(select(Side).order_by(Side.id))).scalars().all()
        maps = (await session.execute(select(Map).order_by(Map.id))).scalars().all()
        characters = (
            await session.execute(
                select(Character).options(selectinload(Character.role)).order_by(Character.name)
            )
        ).scalars().all()
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        return _db_error_response(exc)

    return {
        "roles": [{"id": r.id, "name": r.name, "description": r.description or ""} for r in roles],
        "sides": [{"id": s.id, "name": s.name} for s in sides],
        "maps": [{"id": m.id, "name": m.name, "description": m.description or ""} for m in maps],
        "characters": [_character_to_dict(c) for c in characters],
    }


@router.get("/articles")
async def list_articles(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
):
    forbidden = _require_admin_api(user)
    if forbidden:
        return forbidden
    try:
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
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        return _db_error_response(exc)
    return {"articles": [_article_to_dict(a) for a in articles]}


@router.get("/articles/{article_id}")
async def get_article(
    article_id: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
):
    forbidden = _require_admin_api(user)
    if forbidden:
        return forbidden
    try:
        article = await _load_article(session, article_id)
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        return _db_error_response(exc)
    if not article:
        return JSONResponse({"error": "Article not found"}, status_code=404)
    return {"article": _article_to_dict(article)}


@router.post("/articles")
async def create_article(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
):
    forbidden = _require_admin_api(user)
    if forbidden:
        return forbidden
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    csrf_error = _check_csrf(request, body)
    if csrf_error:
        return csrf_error

    data, err = _parse_article_payload(body if isinstance(body, dict) else {})
    if err:
        return JSONResponse({"error": err}, status_code=400)

    try:
        ref_err = await _validate_article_refs(session, data)
        if ref_err:
            return JSONResponse({"error": ref_err}, status_code=400)

        article = Article(
            title=data["title"],
            content=data["content"],
            map_id=data["map_id"],
            side_id=data["side_id"],
            role_id=data["role_id"],
        )
        await _apply_article_characters(session, article, data["character_ids"])
        session.add(article)
        await session.commit()
        created = await _load_article(session, article.id)
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        try:
            await session.rollback()
        except Exception:
            pass
        return _db_error_response(exc)

    if not created:
        return JSONResponse({"error": "Article not found after create"}, status_code=500)
    return JSONResponse({"article": _article_to_dict(created)}, status_code=201)


@router.put("/articles/{article_id}")
async def update_article(
    article_id: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
):
    forbidden = _require_admin_api(user)
    if forbidden:
        return forbidden
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    csrf_error = _check_csrf(request, body)
    if csrf_error:
        return csrf_error

    data, err = _parse_article_payload(body if isinstance(body, dict) else {})
    if err:
        return JSONResponse({"error": err}, status_code=400)

    try:
        article = await _load_article(session, article_id)
        if not article:
            return JSONResponse({"error": "Article not found"}, status_code=404)

        ref_err = await _validate_article_refs(session, data)
        if ref_err:
            return JSONResponse({"error": ref_err}, status_code=400)

        article.title = data["title"]
        article.content = data["content"]
        article.map_id = data["map_id"]
        article.side_id = data["side_id"]
        article.role_id = data["role_id"]
        await _apply_article_characters(session, article, data["character_ids"])
        await session.commit()
        updated = await _load_article(session, article_id)
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        try:
            await session.rollback()
        except Exception:
            pass
        return _db_error_response(exc)

    if not updated:
        return JSONResponse({"error": "Article not found"}, status_code=404)
    return {"article": _article_to_dict(updated)}


@router.delete("/articles/{article_id}")
async def delete_article(
    article_id: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
):
    forbidden = _require_admin_api(user)
    if forbidden:
        return forbidden
    try:
        body = await request.json()
    except Exception:
        body = {}
    csrf_error = _check_csrf(request, body if isinstance(body, dict) else {})
    if csrf_error:
        return csrf_error

    try:
        article = await session.get(Article, article_id)
        if not article:
            return JSONResponse({"error": "Article not found"}, status_code=404)
        await session.delete(article)
        await session.commit()
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        try:
            await session.rollback()
        except Exception:
            pass
        return _db_error_response(exc)
    return {"ok": True, "deleted_id": article_id}


@router.get("/characters")
async def list_characters(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
):
    forbidden = _require_admin_api(user)
    if forbidden:
        return forbidden
    try:
        result = await session.execute(
            select(Character).options(selectinload(Character.role)).order_by(Character.name)
        )
        characters = result.scalars().all()
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        return _db_error_response(exc)
    return {"characters": [_character_to_dict(c) for c in characters]}


@router.put("/characters/{character_id}")
async def update_character(
    character_id: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
):
    forbidden = _require_admin_api(user)
    if forbidden:
        return forbidden
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    csrf_error = _check_csrf(request, body)
    if csrf_error:
        return csrf_error
    if not isinstance(body, dict):
        return JSONResponse({"error": "Body must be a JSON object"}, status_code=400)

    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        return JSONResponse({"error": "Field 'name' is required"}, status_code=400)
    name = name.strip()
    if len(name) > 128:
        return JSONResponse({"error": "Field 'name' must be at most 128 characters"}, status_code=400)

    description = body.get("description")
    if description is None:
        description = ""
    if not isinstance(description, str):
        return JSONResponse({"error": "Field 'description' must be a string"}, status_code=400)

    icon_url = body.get("icon_url")
    if icon_url is None:
        icon_url = ""
    if not isinstance(icon_url, str):
        return JSONResponse({"error": "Field 'icon_url' must be a string"}, status_code=400)
    icon_url = icon_url.strip()
    if len(icon_url) > 512:
        return JSONResponse({"error": "Field 'icon_url' must be at most 512 characters"}, status_code=400)

    role_id, err = _clean_optional_int(body.get("role_id"), "role_id")
    if err:
        return JSONResponse({"error": err}, status_code=400)

    try:
        character = await session.execute(
            select(Character).options(selectinload(Character.role)).where(Character.id == character_id)
        )
        character = character.scalar_one_or_none()
        if not character:
            return JSONResponse({"error": "Character not found"}, status_code=404)

        if role_id is not None and not await session.get(Role, role_id):
            return JSONResponse({"error": "Role not found"}, status_code=400)

        # Ensure unique name if changed
        if name != character.name:
            existing = await session.execute(
                select(Character.id).where(Character.name == name, Character.id != character_id)
            )
            if existing.scalar_one_or_none() is not None:
                return JSONResponse({"error": "Character with this name already exists"}, status_code=409)

        character.name = name
        character.role_id = role_id
        character.description = description
        character.icon_url = icon_url or None

        await session.commit()
        updated = await session.execute(
            select(Character).options(selectinload(Character.role)).where(Character.id == character_id)
        )
        updated = updated.scalar_one_or_none()
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        try:
            await session.rollback()
        except Exception:
            pass
        return _db_error_response(exc)

    if not updated:
        return JSONResponse({"error": "Character not found"}, status_code=404)
    return {"character": _character_to_dict(updated)}