import pytest


@pytest.mark.asyncio
async def test_health_reports_knowledge_base_loaded(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["knowledge_base_chunks"] > 0
    assert "active_provider" in data


@pytest.mark.asyncio
async def test_config_lists_all_providers(client):
    resp = await client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    provider_names = {p["provider"] for p in data["providers"]}
    assert provider_names == {"anthropic", "openai", "ollama"}
