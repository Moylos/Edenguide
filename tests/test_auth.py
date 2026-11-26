import re
import pytest


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "CSRF token not found in HTML"
    return m.group(1)


@pytest.mark.anyio
async def test_login_page_renders(client):
    resp = await client.get("/login")
    assert resp.status_code == 200
    assert "Вход" in resp.text


@pytest.mark.anyio
async def test_login_logout_and_profile(client, seed_users):
    # Unauthenticated profile -> redirect to /login
    resp = await client.get("/profile", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert "/login" in resp.headers.get("location", "")

    # Get CSRF from login page
    page = await client.get("/login")
    csrf = _extract_csrf(page.text)

    # Wrong password
    bad = await client.post(
        "/login",
        data={"login": "admin", "password": "wrong", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert bad.status_code == 401

    # Correct login
    page = await client.get("/login")
    csrf = _extract_csrf(page.text)
    ok = await client.post(
        "/login",
        data={"login": "admin", "password": "admin123", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert ok.status_code == 303
    assert ok.headers.get("location") == "/profile"

    # Profile accessible after login
    profile = await client.get("/profile")
    assert profile.status_code == 200
    assert "admin" in profile.text

    # Logout
    csrf = _extract_csrf(profile.text)
    out = await client.post(
        "/logout",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert out.status_code == 303

    # Profile again requires login
    resp2 = await client.get("/profile", follow_redirects=False)
    assert resp2.status_code in (302, 303)
