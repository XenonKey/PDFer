import uuid


async def test_register_login_me(client):
    email = f"{uuid.uuid4()}@example.com"
    password = "correct horse battery staple"

    register_resp = await client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert register_resp.status_code == 201
    assert register_resp.json()["email"] == email

    login_resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email


async def test_register_duplicate_email_rejected(client):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "full_name": "Test User"}

    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 400


async def test_login_wrong_password_rejected(client):
    email = f"{uuid.uuid4()}@example.com"
    await client.post(
        "/auth/register", json={"email": email, "password": "correct-password", "full_name": "Test User"}
    )

    resp = await client.post("/auth/login", json={"email": email, "password": "wrong-password"})
    assert resp.status_code == 401


async def test_me_requires_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
