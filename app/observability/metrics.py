from fastapi import FastAPI
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator


def init_metrics(app: FastAPI) -> None:
    """Expose automatic HTTP metrics (requests, latency, in-progress) at GET /metrics."""

    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health"],
        inprogress_name="http_requests_inprogress",
    ).instrument(app).expose(app, endpoint="/metrics", tags=["default"])



claude_requests_total = Counter(
    "claude_requests_total",
    "Claude API calls, grouped by how they finished",
    ["template_slug", "status"],  # status: ok | error | refused | truncated | empty
)

claude_request_duration_seconds = Histogram(
    "claude_request_duration_seconds",
    "Time spent waiting on a Claude API call, in seconds",
    ["template_slug"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

claude_tokens_total = Counter(
    "claude_tokens_total",
    "Tokens consumed by Claude API calls",
    ["template_slug", "token_type"],  # token_type: input | output
)
