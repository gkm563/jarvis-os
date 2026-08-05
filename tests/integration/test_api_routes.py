"""
Integration Tests for FastAPI REST Endpoints & Web Dashboard.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from jarvis.api.server import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"


@pytest.mark.asyncio
async def test_dashboard_ui():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "<title>JARVIS OS" in response.text


@pytest.mark.asyncio
async def test_submit_intent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"user_goal": "Open Chrome and search AKTU results", "execute_immediately": False}
        response = await client.post("/v1/intent", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "plan_id" in data
        assert data["user_goal"] == "Open Chrome and search AKTU results"


@pytest.mark.asyncio
async def test_list_agents():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/agents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0


@pytest.mark.asyncio
async def test_pending_approvals():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/pending_approvals")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
