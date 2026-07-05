# Metrics reference

Everything this service exposes at `GET /metrics` (scraped by Prometheus, see `prometheus.yml`,
graphed in Grafana). Wiring lives in `app/observability/metrics.py`.

## Automatic HTTP metrics (`prometheus-fastapi-instrumentator`)

`init_metrics()` calls `Instrumentator().instrument(app)` without adding any custom collectors,
so the library falls back to its built-in default set:

| Metric | Type | Labels | What it means |
|---|---|---|---|
| `http_requests_total` | Counter | `method`, `handler`, `status` | Requests served, per route + raw status code (not grouped into 2xx/3xx — `should_group_status_codes=False`) |
| `http_request_duration_seconds` | Histogram | `method`, `handler` | Request latency |
| `http_request_duration_highr_seconds` | Histogram | — | Same latency, finer buckets, handy for p99 |
| `http_request_size_bytes` | Summary | `method`, `handler` | Request body size |
| `http_response_size_bytes` | Summary | `method`, `handler` | Response body size |
| `http_requests_inprogress` | Gauge | `method`, `handler` | Requests currently being handled |

`/metrics` and `/health` are excluded (`excluded_handlers`), and requests to routes with no
matching path template are dropped (`should_ignore_untemplated=True`) so a 404-probing bot
can't blow up the `handler` label's cardinality.

## Custom metrics: Claude API calls

Recorded around every `client.messages.create(...)` call in `app/services/extraction.py`
(`_ask_claude`). Not emitted on a cache hit — those return before Claude is ever called.

| Metric | Type | Labels | What it means |
|---|---|---|---|
| `claude_requests_total` | Counter | `template_slug`, `status` | One increment per Claude call. `status` is `ok`, `error` (network/API failure), `refused`, `truncated` (hit `max_tokens`), or `empty` (no text block in the reply) |
| `claude_request_duration_seconds` | Histogram | `template_slug` | Wall-clock time of the Claude call, buckets tuned for LLM latency (0.5s–30s) |
| `claude_tokens_total` | Counter | `template_slug`, `token_type` | Tokens consumed; `token_type` is `input` or `output`. Multiply by your model's per-token price to estimate spend per template |

The same numbers are also logged as structured JSON on every successful call
(`logger.info("Claude extraction succeeded", extra={...})`), so you can cross-check a metric
spike against the actual request in Loki/Grafana.

## Useful PromQL

- Claude error rate: `rate(claude_requests_total{status!="ok"}[5m])`
- Claude p95 latency: `histogram_quantile(0.95, rate(claude_request_duration_seconds_bucket[5m]))`
- Token spend by template: `sum by (template_slug) (rate(claude_tokens_total[1h]))`
- API error rate overall: `rate(http_requests_total{status=~"5.."}[5m])`
