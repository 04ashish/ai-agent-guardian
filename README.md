# AI Agent Guardian
**An automated AI governance & cost gateway** — flags data-leak risk, estimates cost, and logs every AI request before it reaches a model.

Built as a final-year-project-worthy demo of the top pain points companies care about right now: AI security leaks, uncontrolled AI spend, and lack of an audit trail for AI usage.

---

## What it does

Every prompt submitted through the dashboard is routed through the Guardian, which:

1. **Scans for sensitive data** — emails, Indian mobile numbers, card numbers, Aadhaar-like numbers, API keys, and password fields — using regex pattern matching.
2. **Scores risk** — none / low / medium / high, based on how many and which patterns matched.
3. **Blocks high-risk requests** before they'd reach a real model.
4. **Estimates token usage and cost** for every request (input + simulated output).
5. **Logs everything** to a SQLite audit trail — timestamp, prompt, risk level, blocked/allowed, tokens, cost.
6. **Returns a response** — simulated by default (no API key needed), or you can wire in a real LLM call (see below).
7. **Visualizes it all** on a live dashboard: total spend, blocked-request rate, risk breakdown, and requests-over-time.

## Tech stack

- **Backend:** Python, FastAPI, SQLite (no external DB needed)
- **Frontend:** Single-file HTML/CSS/JS dashboard + Chart.js (no build step, no npm needed)

---

## Run it locally (2 minutes)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Then open **http://localhost:8000** in your browser — the backend serves the dashboard directly, so that's the only URL you need. API docs are at `http://localhost:8000/docs`.

That's it — try the "Try a risky example" button to see a request get blocked.

---

## Project structure

```
ai-agent-guardian/
├── backend/
│   ├── main.py           # FastAPI app: risk detection, cost estimation, logging, API routes
│   ├── requirements.txt
│   └── guardian.db       # created automatically on first run (SQLite)
├── frontend/
│   └── index.html        # single-file dashboard (HTML + CSS + JS, Chart.js via CDN)
└── README.md
```

---

## Deploying it for free

The whole app is one Python service (FastAPI serves the dashboard too), so it deploys anywhere that runs Python:

### Render.com (recommended — free tier, simplest)
1. Push this folder to a GitHub repo.
2. On [render.com](https://render.com) → New → Web Service → connect the repo.
3. Root directory: `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy. Your live URL will serve the dashboard directly.

### Railway.app
Same idea — set the root to `backend`, start command `uvicorn main:app --host 0.0.0.0 --port $PORT`.

### Fly.io / any VPS
Standard `uvicorn`/`gunicorn` deployment — no special config needed since there's no separate frontend build step.

> **Note on SQLite in production:** SQLite writes to a local file, which is fine for a demo/portfolio project but resets on most free-tier redeploys (ephemeral filesystem). For a persistent production version, swap `sqlite3` for Postgres (Render/Railway both offer free Postgres) — the `get_db()` function in `main.py` is the only place that would need to change.

---

## Wiring in a real LLM (optional, for a stronger demo)

Right now `simulate_llm_response()` in `backend/main.py` returns a canned response so the project runs with zero API keys. To make it call a real model:

1. Add your API key as an environment variable (e.g. `ANTHROPIC_API_KEY`).
2. Replace the body of `simulate_llm_response()` with a real API call, **but only when `blocked` is `False`** — that's the whole point of the gateway.
3. Everything else (risk detection, cost logging, dashboard) keeps working unchanged.

---

## What to say about it in an interview / on your resume

> "Built an AI governance and cost-control gateway that intercepts AI requests, flags PII/credential leakage using pattern matching, blocks high-risk requests before they reach a model, and tracks token spend with a live analytics dashboard — addressing the two biggest enterprise AI adoption blockers: data leakage and uncontrolled cost."

Talking points if asked to go deeper:
- **Why regex and not an ML classifier?** Fast, deterministic, zero inference cost, explainable — a reasonable v1 for a rules-based gateway. A natural v2 extension is a lightweight NER/classifier model for softer PII types.
- **Why SQLite?** Zero-config persistence, swappable for Postgres in one function.
- **Scaling:** the same gateway pattern is how real AI-governance products (e.g. LLM proxies) work — add a real model call, rate limiting, and per-user budgets, and you have a production-grade version.
