# AI Agent Guardian

**An automated AI governance & cost-control gateway.**

AI Agent Guardian sits between users and an LLM, screening every request for sensitive-data leakage, blocking high-risk prompts before they reach a model, estimating token cost, and logging a full audit trail — all visualized on a live analytics dashboard.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-embedded-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Overview

Enterprise AI adoption is commonly blocked by two problems: employees leaking sensitive data into AI tools, and AI spend that's difficult to track or control. AI Agent Guardian addresses both by acting as a governance layer in front of any LLM integration.

Every prompt passes through the gateway, which:

1. **Screens for sensitive data** — emails, Indian mobile numbers, card numbers, Aadhaar-style numbers, API keys, and password fields, using pattern-based detection.
2. **Assigns a risk score** — `none` / `low` / `medium` / `high`, based on which patterns matched.
3. **Blocks high-risk requests** before they would reach a model.
4. **Estimates token usage and cost** for every request.
5. **Logs a complete audit trail** to SQLite — timestamp, prompt, risk level, outcome, tokens, cost.
6. **Returns a response** — simulated by default for a zero-dependency demo, or wired to a real LLM in one function.
7. **Visualizes usage** on a live dashboard — total spend, blocked-request rate, risk distribution, and request volume over time.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript, Chart.js |

No build tooling required on either side — the backend serves the frontend directly as a single deployable service.

## Project Structure

```
ai-agent-guardian/
├── backend/
│   ├── main.py           # API routes, risk detection, cost estimation, logging
│   ├── requirements.txt
│   └── guardian.db       # created automatically on first run
├── frontend/
│   └── index.html        # dashboard (HTML/CSS/JS, Chart.js via CDN)
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.10+

### Installation

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### Run

```bash
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** — the backend serves the dashboard directly. Interactive API documentation is available at **http://localhost:8000/docs**.

## Deployment

The application is a single Python service, so it deploys anywhere that supports Python web services.

**Render (recommended)**
1. Push this repository to GitHub.
2. On [render.com](https://render.com): New → Web Service → connect the repository.
3. Root directory: `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Railway** follows the same configuration. Any standard `uvicorn`/`gunicorn`-compatible host works, since there is no separate frontend build step.

> **Note:** SQLite persists to a local file, which is reset on redeploy on most free-tier hosts. For a production deployment with persistent storage, replace SQLite with Postgres — the `get_db()` function in `main.py` is the only integration point that requires changes.

## Extending to a Real LLM

By default, `simulate_llm_response()` in `backend/main.py` returns a canned response so the project runs with no API keys required. To connect a real model:

1. Store your API key as an environment variable.
2. Replace the body of `simulate_llm_response()` with a real API call — invoked only when `blocked` is `False`.
3. Risk detection, cost logging, and the dashboard require no changes.

## Design Notes

- **Pattern matching over ML classification:** deterministic, zero inference cost, and fully explainable — a reasonable first line of defense for a rules-based gateway. A natural extension is a lightweight NER model for softer PII categories.
- **SQLite for persistence:** zero-configuration storage suited to a demo deployment, with a single swap point to Postgres for production use.
- **Single-service architecture:** the backend serves the frontend directly, removing the need for a separate static hosting setup or build pipeline.

## License

MIT
