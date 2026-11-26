import re

import pytest


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "CSRF token not found in HTML"
    return m.group(1)


async def _login(client, login: str, password: str) -> str:
    page = await client.get("/login")
    csrf = _extract_csrf(page.text)
    resp = await client.post(
        "/login",
        data={"login": login, "password": password, "csrf_token": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    profile = await client.get("/profile")
    assert profile.status_code == 200
    return _extract_csrf(profile.text)


@pytest.mark.anyio
async def test_get_tierlist_default(client):
    resp = await client.get("/api/tierlist")
    assert resp.status_code == 200
    data = resp.json()
    assert "tiers" in data
    assert "pool" in data
    assert isinstance(data["tiers"], list)
    assert len(data["tiers"]) == 5
    assert [t["id"] for t in data["tiers"]] == ["S", "A", "B", "C", "D"]
    assert data["pool"] == []


@pytest.mark.anyio
async def test_put_tierlist_requires_admin(client, seed_users):
    csrf = await _login(client, "student", "student123")
    resp = await client.put(
        "/api/tierlist",
        json={"tiers": [], "pool": []},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_put_tierlist_requires_auth(client):
    resp = await client.put(
        "/api/tierlist",
        json={"tiers": [], "pool": []},
        headers={"X-CSRF-Token": "bad"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_put_tierlist_invalid_csrf(client, seed_users):
    await _login(client, "admin", "admin123")
    resp = await client.put(
        "/api/tierlist",
        json={"tiers": [], "pool": []},
        headers={"X-CSRF-Token": "invalid"},
    )
    assert resp.status_code == 403
    assert resp.json().get("error")


@pytest.mark.anyio
async def test_put_and_get_tierlist_persists(client, seed_users):
    csrf = await _login(client, "admin", "admin123")
    payload = {
        "tiers": [
            {"id": "S", "label": "S", "color": "#e74c3c", "items": ["jett", "raze"]},
            {"id": "A", "label": "A", "color": "#e67e22", "items": ["sova"]},
            {"id": "B", "label": "B", "color": "#f1c40f", "items": []},
            {"id": "C", "label": "C", "color": "#2ecc71", "items": []},
            {"id": "D", "label": "D", "color": "#3498db", "items": []},
        ],
        "pool": ["omen"],
    }
    put_resp = await client.put(
        "/api/tierlist",
        json=payload,
        headers={"X-CSRF-Token": csrf},
    )
    assert put_resp.status_code == 200
    assert put_resp.json() == payload

    get_resp = await client.get("/api/tierlist")
    assert get_resp.status_code == 200
    assert get_resp.json() == payload


@pytest.mark.anyio
async def test_put_tierlist_invalid_structure(client, seed_users):
    csrf = await _login(client, "admin", "admin123")
    resp = await client.put(
        "/api/tierlist",
        json={"tiers": "nope", "pool": []},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.anyio
async def test_tierlist_page_has_is_admin(client, seed_users, monkeypatch):
    from api.routers import public as public_router

    captured = []
    real = public_router.templates.TemplateResponse

    def fake(request, name, context=None, *args, **kwargs):
        captured.append({"name": name, "context": context or {}})
        return real(request, name, context, *args, **kwargs)

    monkeypatch.setattr(public_router.templates, "TemplateResponse", fake)

    resp = await client.get("/tierlist")
    assert resp.status_code == 200
    assert captured[-1]["context"].get("is_admin") is False

    await _login(client, "admin", "admin123")
    resp_admin = await client.get("/tierlist")
    assert resp_admin.status_code == 200
    assert captured[-1]["context"].get("is_admin") is True
