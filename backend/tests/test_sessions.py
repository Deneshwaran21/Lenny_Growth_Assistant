import pytest


@pytest.mark.asyncio
async def test_create_and_fetch_session(client):
    resp = await client.post("/api/sessions", json={"user_id": "denesh"})
    assert resp.status_code == 201
    session = resp.json()
    assert session["user_id"] == "denesh"
    assert session["provider"] in {"anthropic", "openai", "ollama"}

    resp2 = await client.get(f"/api/sessions/{session['id']}")
    assert resp2.status_code == 200
    assert resp2.json()["id"] == session["id"]


@pytest.mark.asyncio
async def test_sessions_are_independent_per_user(client):
    await client.post("/api/sessions", json={"user_id": "alice"})
    await client.post("/api/sessions", json={"user_id": "bob"})

    alice_sessions = (await client.get("/api/sessions", params={"user_id": "alice"})).json()
    bob_sessions = (await client.get("/api/sessions", params={"user_id": "bob"})).json()

    assert len(alice_sessions) == 1
    assert len(bob_sessions) == 1
    assert alice_sessions[0]["id"] != bob_sessions[0]["id"]


@pytest.mark.asyncio
async def test_get_nonexistent_session_returns_404(client):
    resp = await client.get("/api/sessions/does-not-exist")
    assert resp.status_code == 404
