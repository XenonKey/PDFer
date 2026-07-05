# pdfer

A backend service that turns structured input — or free-form text — into generated
documents. A user picks a `Template` (a JSON schema plus an HTML template) by slug,
then either submits `input_data` directly or submits free text that Claude turns
into `input_data` matching that template's schema. Generation runs asynchronously
on a Celery worker.

The interesting part is how the LLM is wired in: the free-text call is constrained
to the template's own JSON schema so it can only extract fields, never invent
structure; the call is cached, and its latency, token spend, and failure modes are
tracked like any other external dependency; and a small chat agent can call a tool
against the app's own data to answer status questions.

## What it does

**Structured flow**: `POST /requests` with a `template_slug` and an `input_data`
dict. The payload is validated against the template's JSON schema before a
`DocumentRequest` row is created and handed to Celery.

**Free-text flow**: `POST /requests/from-text` with a `template_slug` and `text`.
The text and the template's schema are sent to Claude with the response constrained
to that schema (`output_config={"format": {"type": "json_schema", ...}}`), so the
model only ever fills in fields the template defines — it never picks the template
itself. The extracted result goes through the same JSON-schema validation as the
structured flow before a request is created.

**Chat agent**: `POST /chat/job-status` lets a user ask, in natural language, about
the status of a request. Claude decides whether to answer directly or call a tool
(`get_extraction_job_status`) that looks up the request in the database, then
folds the result back into a natural-language answer.

## Architecture

- **API** (`app/main.py`, `app/routers/`): FastAPI, JWT auth (`app/security.py`),
  async SQLAlchemy for request handlers.
- **Workers** (`app/tasks/`): Celery, sync SQLAlchemy session (`SyncSessionLocal`
  in `app/database.py`) since Celery workers are sync. `generate_document` flips a
  request `pending → processing → completed/failed` and writes the output file;
  `send_notification` fires once generation succeeds.
- **Scheduled jobs** (`app/celery_app.py` `beat_schedule`): `reap_stuck_requests`
  fails requests that have been stuck in `processing` past a timeout (e.g. a worker
  died mid-job); `cleanup_old_generated_docs` prunes old output files.
- **Extraction** (`app/services/extraction.py`): the Claude call for the free-text
  flow, with Redis caching (identical `template` + `text` never calls Claude twice)
  and Prometheus metrics for call count, latency, and token usage.
- **Caching** (`app/cache.py`): Redis-backed, for the template list/detail and each
  user's request list. Routers invalidate the relevant keys on writes — there's no
  automatic invalidation, so new mutating endpoints need to call `delete_cached`
  themselves.
- **Observability**: JSON-structured logs shipped by Promtail into Loki, Prometheus
  metrics at `/metrics` (scraped per `prometheus.yml`, alerting via
  `alert_rules.yml`/`alertmanager.yml`), Grafana for dashboards. See
  `app/observability/METRICS.md` for what's exposed and useful PromQL.

Two database engines exist on purpose: `async_engine`/`AsyncSessionLocal` for the
FastAPI app, `sync_engine`/`SyncSessionLocal` for Celery tasks (Celery doesn't do
async). Both point at the same Postgres instance.

## Known limitations

A few things are intentionally simplified at this stage:

- **Document generation is a stub.** `generate_pdf_file` in `app/tasks/documents.py`
  writes a plaintext file with a `.pdf` extension instead of rendering
  `Template.html_template` to a real PDF. Swapping in a real renderer (Jinja2 +
  WeasyPrint, for example) only touches that one function.
- **Notifications are a stub.** `send_notification` prints instead of sending a
  real email or webhook; the `Notification` row it writes already models both.
- **Generated files live on local disk** (`generated_docs/`, bind-mounted in
  `docker-compose.override.yml`), not in object storage. That's fine for one
  container; it won't survive a redeploy or work across multiple instances.
- **Cancelling a request doesn't revoke an in-flight Celery task** — it only
  prevents processing if the task hasn't started yet, since the request doesn't
  store its Celery task id. In practice the cancel window is very short: since
  the stub generator does no real rendering work, a request often reaches
  `completed` before a cancel request can land.
- **Tests run against the local dev stack** (real Postgres/Redis via the Docker
  network) rather than an isolated test database — fine for local development, but
  a dedicated test database and fixtures would be needed to run this in CI.

## Running it

```
docker-compose up --build
```

This brings up the API, two Celery workers (`documents`, `notifications`), Celery
beat, Postgres, Redis, RabbitMQ, and the observability stack. The override file
(`docker-compose.override.yml`) adds bind mounts, `--reload`, and exposed ports for
local dev.

| Service | URL |
|---|---|
| API | http://localhost:8000 (docs at `/docs`) |
| Flower (Celery monitoring) | http://localhost:5555 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| RabbitMQ management | http://localhost:15672 |

Copy `.env.example` to `.env` and fill in the values — most fields are required
with no defaults, so the app won't start with an incomplete `.env`. You'll need
your own `ANTHROPIC_API_KEY` for the free-text extraction and chat endpoints to
work.

Database migrations run against Postgres via Alembic:

```
uv run alembic upgrade head
```

### Running the API without Docker

```
uv sync
uv run uvicorn app.main:app --reload
```

This still needs Postgres, Redis, and RabbitMQ reachable at whatever `DATABASE_URL`
/ `REDIS_URL` / `CELERY_BROKER_URL` you configure.

## Tests

```
docker compose exec api pytest
```

A thin suite: auth (register/login/me, duplicate email, bad password), request
creation (schema validation, unknown template, the cancel-status transition), and
the extraction service's handling of Claude's `refusal` / `max_tokens` stop
reasons, with the Anthropic client mocked.

## Linting

```
uv run ruff check .
```

## Dependency changes

The Docker image installs from `requirements.txt`, not `pyproject.toml`/`uv.lock`
directly. After changing dependencies, regenerate it:

```
uv lock
uv export --no-dev --no-hashes -o requirements.txt
```
