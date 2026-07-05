import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models import Template
from app.services.extraction import ExtractionError, extract_input_data


def _template(schema: dict) -> Template:
    return Template(name="Invoice", slug="invoice", schema=schema, html_template="<p></p>")


def _response(*, stop_reason="end_turn", text=None, input_tokens=10, output_tokens=5):
    content = [SimpleNamespace(type="text", text=text)] if text is not None else []
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=content,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


@pytest.fixture(autouse=True)
def no_cache():
    with (
        patch("app.services.extraction.get_cached", AsyncMock(return_value=None)),
        patch("app.services.extraction.set_cached", AsyncMock(return_value=None)),
    ):
        yield


async def test_extract_input_data_success():
    template = _template({"type": "object", "properties": {"amount": {"type": "number"}}})
    reply = _response(text=json.dumps({"amount": 42}))

    with patch("app.services.extraction.client.messages.create", AsyncMock(return_value=reply)):
        result = await extract_input_data("Bill them 42 dollars", template)

    assert result == {"amount": 42}


async def test_extract_input_data_refusal_raises():
    template = _template({"type": "object", "properties": {}})
    reply = _response(stop_reason="refusal")

    with patch("app.services.extraction.client.messages.create", AsyncMock(return_value=reply)):
        with pytest.raises(ExtractionError):
            await extract_input_data("some text", template)


async def test_extract_input_data_truncated_raises():
    template = _template({"type": "object", "properties": {}})
    reply = _response(stop_reason="max_tokens")

    with patch("app.services.extraction.client.messages.create", AsyncMock(return_value=reply)):
        with pytest.raises(ExtractionError):
            await extract_input_data("some text", template)
