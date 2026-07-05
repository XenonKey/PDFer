import json
import logging
import time

import anthropic
from anthropic import AsyncAnthropic

from app.cache import CacheKeys, CacheTTL, get_cached, set_cached
from app.config import settings
from app.models import Template
from app.observability.metrics import claude_request_duration_seconds, claude_requests_total, claude_tokens_total

logger = logging.getLogger(__name__)

client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


class ExtractionError(Exception):
    """Claude could not extract valid input_data from the text."""


async def extract_input_data(text: str, template: Template) -> dict:
    cache_key = CacheKeys.extraction(str(template.id), text)
    cached = await get_cached(cache_key)
    if isinstance(cached, dict):
        logger.info("Extraction cache hit", extra={"template_slug": template.slug})
        return cached

    input_data = await _ask_claude(text, template)

    await set_cached(cache_key, input_data, CacheTTL.EXTRACTION)
    return input_data


async def _ask_claude(text: str, template: Template) -> dict:
    """Ask Claude to fill in the template's schema from free text, and return the parsed result."""

    schema = dict(template.schema)
    schema["additionalProperties"] = False

    started_at = time.perf_counter()
    try:
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            thinking={"type": "disabled"},
            system=(
                f'Extract the fields needed for the document template "{template.name}" from the '
                "user's request. Only fill in fields that are explicitly stated or unambiguously "
                "implied by the text."
            ),
            output_config={"format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": text}],
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        claude_requests_total.labels(template_slug=template.slug, status="error").inc()
        logger.warning("Claude call failed: %s", exc, extra={"template_slug": template.slug})
        raise ExtractionError("Failed to reach Claude") from exc

    duration_seconds = time.perf_counter() - started_at
    claude_request_duration_seconds.labels(template_slug=template.slug).observe(duration_seconds)
    claude_tokens_total.labels(template_slug=template.slug, token_type="input").inc(response.usage.input_tokens)
    claude_tokens_total.labels(template_slug=template.slug, token_type="output").inc(response.usage.output_tokens)

    input_data = _read_json_reply(response, template.slug)

    claude_requests_total.labels(template_slug=template.slug, status="ok").inc()
    logger.info(
        "Claude extraction succeeded",
        extra={
            "template_slug": template.slug,
            "duration_seconds": round(duration_seconds, 3),
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    )
    return input_data


def _read_json_reply(response: anthropic.types.Message, template_slug: str) -> dict:
    
    if response.stop_reason == "refusal":
        claude_requests_total.labels(template_slug=template_slug, status="refused").inc()
        raise ExtractionError("Claude declined to process the request")
    if response.stop_reason == "max_tokens":
        claude_requests_total.labels(template_slug=template_slug, status="truncated").inc()
        raise ExtractionError("Claude's response was truncated")

    text_block = next((block for block in response.content if block.type == "text"), None)
    if text_block is None:
        claude_requests_total.labels(template_slug=template_slug, status="empty").inc()
        raise ExtractionError("Claude did not return a text response")

    return json.loads(text_block.text)
