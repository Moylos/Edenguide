import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.deps import current_user
from api.models import TierlistState, User
from api.security import validate_csrf_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

DEFAULT_TIERLIST_STATE: dict = {
    "tiers": [
        {"id": "S", "label": "S", "color": "#e74c3c", "items": []},
        {"id": "A", "label": "A", "color": "#e67e22", "items": []},
        {"id": "B", "label": "B", "color": "#f1c40f", "items": []},
        {"id": "C", "label": "C", "color": "#2ecc71", "items": []},
        {"id": "D", "label": "D", "color": "#3498db", "items": []},
    ],
    "pool": [],
}


def _default_state() -> dict:
    return json.loads(json.dumps(DEFAULT_TIERLIST_STATE))


def _extract_csrf_token(request: Request, body: dict) -> str | None:
    header_token = request.headers.get("X-CSRF-Token")
    if header_token:
        return header_token
    body_token = body.get("csrf_token")
    if isinstance(body_token, str):
        return body_token
    return None


def _validate_state(payload: dict) -> tuple[dict | None, str | None]:
    if not isinstance(payload, dict):
        return None, "Body must be a JSON object"

    tiers = payload.get("tiers")
    pool = payload.get("pool")
    if not isinstance(tiers, list):
        return None, "Field 'tiers' must be a list"
    if not isinstance(pool, list):
        return None, "Field 'pool' must be a list"

    normalized_tiers = []
    for idx, tier in enumerate(tiers):
        if not isinstance(tier, dict):
            return None, f"tiers[{idx}] must be an object"
        tier_id = tier.get("id")
        label = tier.get("label")
        color = tier.get("color")
        items = tier.get("items")
        if not isinstance(tier_id, str) or not tier_id.strip():
            return None, f"tiers[{idx}].id must be a non-empty string"
        if not isinstance(label, str) or not label.strip():
            return None, f"tiers[{idx}].label must be a non-empty string"
        if not isinstance(color, str) or not color.strip():
            return None, f"tiers[{idx}].color must be a non-empty string"
        if not isinstance(items, list):
            return None, f"tiers[{idx}].items must be a list"
        if not all(isinstance(item, str) for item in items):
            return None, f"tiers[{idx}].items must contain only strings"
        normalized_tiers.append(
            {
                "id": tier_id.strip(),
                "label": label.strip(),
                "color": color.strip(),
                "items": [item.strip() for item in items if item.strip()],
            }
        )

    if not all(isinstance(item, str) for item in pool):
        return None, "Field 'pool' must contain only strings"
    normalized_pool = [item.strip() for item in pool if item.strip()]

    return {"tiers": normalized_tiers, "pool": normalized_pool}, None


async def _load_state(session: AsyncSession) -> dict:
    result = await session.execute(
        select(TierlistState).order_by(TierlistState.id.desc()).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return _default_state()
    try:
        data = json.loads(row.state_json)
    except (TypeError, json.JSONDecodeError):
        logger.warning("Invalid tierlist_state JSON in DB, returning default")
        return _default_state()
    normalized, error = _validate_state(data)
    if error:
        logger.warning("Invalid tierlist_state structure in DB: %s", error)
        return _default_state()
    return normalized


@router.get("/tierlist")
async def get_tierlist(
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        state = await _load_state(session)
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        logger.warning("Tierlist read failed, returning default: %s", exc)
        return _default_state()
    return state


@router.put("/tierlist")
async def put_tierlist(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
):
    if not user or user.role != "admin":
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    if not isinstance(body, dict):
        return JSONResponse({"error": "Body must be a JSON object"}, status_code=400)

    csrf_token = _extract_csrf_token(request, body)
    if not validate_csrf_token(request.session.get("csrf_token"), csrf_token):
        return JSONResponse({"error": "Invalid CSRF token"}, status_code=403)

    payload = {k: v for k, v in body.items() if k != "csrf_token"}
    normalized, error = _validate_state(payload)
    if error:
        return JSONResponse({"error": error}, status_code=400)

    state_json = json.dumps(normalized, ensure_ascii=False)
    try:
        result = await session.execute(
            select(TierlistState).order_by(TierlistState.id.desc()).limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            row.state_json = state_json
            row.updated_by = user.id
        else:
            row = TierlistState(state_json=state_json, updated_by=user.id)
            session.add(row)

        await session.commit()
        await session.refresh(row)
    except (SQLAlchemyError, TimeoutError, OSError) as exc:
        logger.warning("Tierlist write failed: %s", exc)
        try:
            await session.rollback()
        except Exception:
            pass
        return JSONResponse(
            {"error": "Service temporarily unavailable: database connection failed."},
            status_code=503,
        )
    return normalized
