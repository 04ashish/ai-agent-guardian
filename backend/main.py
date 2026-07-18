"""
AI Agent Guardian — backend
A lightweight AI governance / cost gateway.

Every "AI request" is routed through this gateway before it would reach a
real LLM. The gateway:
  1. Scans the prompt for data-leak risk (emails, phone numbers, API keys,
     card numbers, Aadhaar-like numbers, passwords).
  2. Estimates token usage and cost.
  3. Blocks or allows the request based on risk level.
  4. Logs everything to SQLite for the audit-trail dashboard.
  5. Returns a simulated LLM response (no real API key needed for the demo).

Run locally:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

API docs will be at http://localhost:8000/docs
"""

import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "guardian.db"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

app = FastAPI(title="AI Agent Guardian", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                user_label TEXT,
                prompt TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                risk_flags TEXT,
                blocked INTEGER NOT NULL,
                tokens_est INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                response TEXT
            )
            """
        )


init_db()

# --------------------------------------------------------------------------
# Risk detection
# --------------------------------------------------------------------------

PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "phone_in": re.compile(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "api_key": re.compile(r"\b(sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{12,}|AIza[0-9A-Za-z_-]{20,})\b"),
    "password_kw": re.compile(r"\b(password|passwd|pwd|secret[_ ]?key|api[_ ]?key)\s*[:=]", re.I),
}

FLAG_WEIGHT = {
    "email": 1,
    "phone_in": 1,
    "credit_card": 3,
    "aadhaar": 3,
    "api_key": 4,
    "password_kw": 3,
}


def analyze_risk(prompt: str):
    flags = []
    score = 0
    for name, pattern in PATTERNS.items():
        if pattern.search(prompt):
            flags.append(name)
            score += FLAG_WEIGHT[name]

    if score == 0:
        level = "none"
    elif score <= 2:
        level = "low"
    elif score <= 4:
        level = "medium"
    else:
        level = "high"

    blocked = level == "high"
    return level, flags, blocked


def estimate_cost(prompt: str, response: str):
    # Rough token estimate: ~1.3 tokens per word, industry rule-of-thumb.
    words = len((prompt + " " + response).split())
    tokens = max(1, int(words * 1.3))
    # Blended demo rate ~ $3 / 1M input+output tokens (illustrative only).
    cost_usd = round((tokens / 1_000_000) * 3.0, 6)
    return tokens, cost_usd


def simulate_llm_response(prompt: str) -> str:
    """No real API key needed — returns a short canned/simulated reply
    so the whole pipeline can be demoed end-to-end offline."""
    snippet = prompt.strip().replace("\n", " ")
    if len(snippet) > 80:
        snippet = snippet[:80] + "..."
    return (
        f"[simulated response] Here's a draft answer addressing: \"{snippet}\". "
        "In a production deployment this would be the real LLM's reply, "
        "returned only after passing the Guardian's safety and cost checks."
    )


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    user_label: Optional[str] = Field(default="demo-user", max_length=100)


class AnalyzeResponse(BaseModel):
    id: str
    created_at: str
    risk_level: str
    risk_flags: list[str]
    blocked: bool
    tokens_est: int
    cost_usd: float
    response: Optional[str]


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    level, flags, blocked = analyze_risk(req.prompt)

    if blocked:
        response_text = None
        tokens, cost = estimate_cost(req.prompt, "")
    else:
        response_text = simulate_llm_response(req.prompt)
        tokens, cost = estimate_cost(req.prompt, response_text)

    record_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        conn.execute(
            """INSERT INTO requests
               (id, created_at, user_label, prompt, risk_level, risk_flags,
                blocked, tokens_est, cost_usd, response)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record_id,
                created_at,
                req.user_label,
                req.prompt,
                level,
                ",".join(flags),
                int(blocked),
                tokens,
                cost,
                response_text,
            ),
        )

    return AnalyzeResponse(
        id=record_id,
        created_at=created_at,
        risk_level=level,
        risk_flags=flags,
        blocked=blocked,
        tokens_est=tokens,
        cost_usd=cost,
        response=response_text,
    )


@app.get("/api/logs")
def get_logs(limit: int = 50):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM requests ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/stats")
def get_stats():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM requests").fetchone()["c"]
        blocked = conn.execute(
            "SELECT COUNT(*) AS c FROM requests WHERE blocked = 1"
        ).fetchone()["c"]
        total_cost = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) AS s FROM requests"
        ).fetchone()["s"]
        total_tokens = conn.execute(
            "SELECT COALESCE(SUM(tokens_est), 0) AS s FROM requests"
        ).fetchone()["s"]
        by_risk = conn.execute(
            "SELECT risk_level, COUNT(*) AS c FROM requests GROUP BY risk_level"
        ).fetchall()
        recent = conn.execute(
            """SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS c,
                      COALESCE(SUM(cost_usd), 0) AS cost
               FROM requests GROUP BY day ORDER BY day DESC LIMIT 14"""
        ).fetchall()

    return {
        "total_requests": total,
        "blocked_requests": blocked,
        "total_cost_usd": round(total_cost, 6),
        "total_tokens": total_tokens,
        "by_risk_level": {r["risk_level"]: r["c"] for r in by_risk},
        "daily": [dict(r) for r in recent][::-1],
    }


@app.delete("/api/logs")
def clear_logs():
    with get_db() as conn:
        conn.execute("DELETE FROM requests")
    return {"status": "cleared"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------------------------------
# Serve the frontend (so the whole app can run as a single service)
# --------------------------------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")
