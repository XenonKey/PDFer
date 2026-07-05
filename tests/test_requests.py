import uuid

import pytest
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import DocumentRequest, Template


async def test_create_request_unknown_template_404(client, auth_headers):
    resp = await client.post(
        "/requests",
        json={"template_slug": "does-not-exist", "input_data": {}},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_create_request_invalid_input_data_422(client, auth_headers):
    resp = await client.post(
        "/requests",
        json={"template_slug": "invoice", "input_data": {"invoice_num": "INV-1"}},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_create_request_valid_input_data_201(client, auth_headers):
    resp = await client.post(
        "/requests",
        json={"template_slug": "invoice", "input_data": {"invoice_num": "INV-1", "amount": 100}},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"


@pytest.fixture
async def pending_request(client, auth_headers):
    me = await client.get("/auth/me", headers=auth_headers)
    user_id = uuid.UUID(me.json()["id"])

    async with AsyncSessionLocal() as db:
        template = (await db.execute(select(Template).where(Template.slug == "invoice"))).scalar_one()
        request = DocumentRequest(
            user_id=user_id,
            template_id=template.id,
            input_data={"invoice_num": "INV-X", "amount": 1},
        )
        db.add(request)
        await db.commit()
        await db.refresh(request)
        return request


async def test_cancel_request_sets_cancelled_status(client, auth_headers, pending_request):
    cancel_resp = await client.delete(f"/requests/{pending_request.id}", headers=auth_headers)
    assert cancel_resp.status_code == 204

    get_resp = await client.get(f"/requests/{pending_request.id}", headers=auth_headers)
    assert get_resp.json()["status"] == "cancelled"


async def test_cancel_already_cancelled_request_rejected(client, auth_headers, pending_request):
    await client.delete(f"/requests/{pending_request.id}", headers=auth_headers)

    second_cancel = await client.delete(f"/requests/{pending_request.id}", headers=auth_headers)
    assert second_cancel.status_code == 400
