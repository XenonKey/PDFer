LANDING_PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pdfer</title>
<meta name="description" content="A FastAPI backend that turns structured or free-text input into generated documents, via async Celery workers and a schema-constrained Claude extraction step.">
<style>
  :root {
    color-scheme: light dark;
    --fg: #1a1a1a;
    --fg-dim: #5a5a5a;
    --bg: #ffffff;
    --border: #e2e2e2;
    --accent: #0b5fff;
    --code-bg: #f4f4f4;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --fg: #e6e6e6;
      --fg-dim: #9a9a9a;
      --bg: #121212;
      --border: #2a2a2a;
      --accent: #5b9cff;
      --code-bg: #1c1c1c;
    }
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--fg);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.55;
    padding: 4rem 1.5rem 3rem;
  }
  main {
    max-width: 640px;
    margin: 0 auto;
  }
  h1 {
    font-size: 1.5rem;
    font-weight: 600;
    margin: 0 0 0.35rem;
    letter-spacing: -0.01em;
  }
  .tagline {
    color: var(--fg-dim);
    margin: 0 0 2rem;
    font-size: 0.95rem;
  }
  p { margin: 0 0 1rem; }
  section { margin-bottom: 2rem; }
  h2 {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--fg-dim);
    font-weight: 600;
    margin: 0 0 0.75rem;
  }
  ol {
    margin: 0;
    padding-left: 1.25rem;
  }
  li { margin-bottom: 0.5rem; }
  li:last-child { margin-bottom: 0; }
  code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 3px;
    padding: 0.1em 0.35em;
    font-size: 0.87em;
  }
  .stack {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.82rem;
    color: var(--fg-dim);
  }
  footer {
    border-top: 1px solid var(--border);
    padding-top: 1.5rem;
    font-size: 0.9rem;
  }
  a {
    color: var(--accent);
    text-decoration: none;
  }
  a:hover { text-decoration: underline; }
  .links a:not(:last-child)::after {
    content: "";
    display: inline-block;
    width: 0.75rem;
  }
</style>
</head>
<body>
<main>
  <header>
    <h1>pdfer</h1>
    <p class="tagline">Backend service for generating documents from structured or free-text input.</p>
  </header>

  <section>
    <p>
      A request picks a <code>Template</code> (JSON schema + HTML template) by slug, then either
      submits <code>input_data</code> directly or submits free text that Claude extracts into
      <code>input_data</code> matching that template's schema &mdash; the model only fills in fields,
      it never chooses the template. Generation and notification run asynchronously on Celery workers.
    </p>
  </section>

  <section>
    <h2>How it works</h2>
    <ol>
      <li>Pick a <code>Template</code> and submit either <code>input_data</code> or free text.</li>
      <li>Free text is extracted by Claude, constrained to the template's JSON schema, then re-validated.</li>
      <li>A Celery worker renders the document and queues a completion notification.</li>
    </ol>
  </section>

  <section class="stack">
    FastAPI &middot; PostgreSQL &middot; Celery &middot; Redis &middot; RabbitMQ &middot; Anthropic Claude &middot; Prometheus / Grafana / Loki
  </section>

  <footer class="links">
    <a href="/docs">API documentation &rarr;</a>
    <a href="/redoc">ReDoc</a>
  </footer>
</main>
</body>
</html>
"""
