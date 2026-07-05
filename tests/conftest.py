import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client):
    email = f"{uuid.uuid4()}@example.com"
    await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test User"},
    )
    login = await client.post("/auth/login", json={"email": email, "password": "password123"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
