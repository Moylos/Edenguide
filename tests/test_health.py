import pytest


@pytest.mark.anyio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_index_renders(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Edenguide" in resp.text
