"""
Fraud detection API. Single FastAPI service handling:
- transaction scoring (XGBoost)
- LLM explanation (with rule-based fallback)
- persistence (SQLite)
- CRUD endpoints for the dashboard

Hackathon-scope note: consolidated into one service for build speed.
Target production architecture splits this into API / AI-layer / DB
layers per the full spec (see docs/ARCHITECTURE.md).
"""
import hashlib
import math
import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from llm_explain import explain_transaction

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "fraud.db"
MODEL_PATH = BASE_DIR / "fraud_model.joblib"

app = FastAPI(title="Fraud Detection API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

bundle = joblib.load(MODEL_PATH)
model = bundle["model"]
FEATURES = bundle["features"]


def _sanitize_for_json(obj):
    """Rejected values like inf/nan echoed back in a validation error aren't
    valid JSON on their own; stringify them so the error response can render
    as 422 instead of failing serialization and surfacing as a 500."""
    if isinstance(obj, float) and not math.isfinite(obj):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    return obj


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": _sanitize_for_json(jsonable_encoder(exc.errors()))},
    )


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distance_from_home REAL,
            distance_from_last_transaction REAL,
            ratio_to_median_purchase REAL,
            repeat_borrower INTEGER,
            used_chip_or_biometric INTEGER,
            used_pin_or_otp INTEGER,
            is_online_channel INTEGER,
            hour_of_day REAL,
            loan_amount REAL,
            fraud_probability REAL,
            risk_level TEXT,
            explanation TEXT,
            recommended_action TEXT,
            source TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


class TransactionIn(BaseModel):
    distance_from_home: float = Field(ge=0, allow_inf_nan=False)
    distance_from_last_transaction: float = Field(ge=0, allow_inf_nan=False)
    ratio_to_median_purchase: float = Field(ge=0, allow_inf_nan=False)
    repeat_borrower: int = Field(ge=0, le=1)
    used_chip_or_biometric: int = Field(ge=0, le=1)
    used_pin_or_otp: int = Field(ge=0, le=1)
    is_online_channel: int = Field(ge=0, le=1)
    hour_of_day: float = Field(ge=0, le=23, allow_inf_nan=False)
    loan_amount: float = Field(gt=0, allow_inf_nan=False)


class StatusUpdate(BaseModel):
    status: Literal["cleared", "flagged"]


# Rejects a second identical submission within this window (e.g. a double-clicked
# submit button or a client retry), without touching the scoring/explanation path.
DUPLICATE_WINDOW_SECONDS = 3
_recent_submissions: dict[str, float] = {}


def _reject_if_duplicate(row: dict):
    key = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
    now = time.monotonic()
    for stale_key in [k for k, ts in _recent_submissions.items() if now - ts > DUPLICATE_WINDOW_SECONDS]:
        del _recent_submissions[stale_key]
    if key in _recent_submissions:
        raise HTTPException(409, "Duplicate transaction submitted too recently")
    _recent_submissions[key] = now


def risk_level_from_prob(p: float) -> str:
    if p >= 0.7:
        return "high"
    if p >= 0.3:
        return "medium"
    return "low"


def top_contributing_features(row: dict, n=3):
    importances = model.feature_importances_
    ranked = sorted(zip(FEATURES, importances), key=lambda x: -x[1])[:n]
    return [{"name": name, "value": float(row[name])} for name, _ in ranked]


def _score_and_store(row: dict) -> dict:
    X = pd.DataFrame([row])[FEATURES]
    prob = float(model.predict_proba(X)[0, 1])
    risk = risk_level_from_prob(prob)
    top_features = top_contributing_features(row)

    result = explain_transaction(prob, risk, top_features)

    conn = get_db()
    cur = conn.execute(
        """INSERT INTO transactions
        (distance_from_home, distance_from_last_transaction, ratio_to_median_purchase,
         repeat_borrower, used_chip_or_biometric, used_pin_or_otp, is_online_channel,
         hour_of_day, loan_amount, fraud_probability, risk_level, explanation,
         recommended_action, source, status, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            row["distance_from_home"], row["distance_from_last_transaction"],
            row["ratio_to_median_purchase"], row["repeat_borrower"],
            row["used_chip_or_biometric"], row["used_pin_or_otp"],
            row["is_online_channel"], row["hour_of_day"], row["loan_amount"],
            prob, risk, result["explanation"], result["recommended_action"],
            result["source"], "pending", datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    txn_id = cur.lastrowid
    conn.close()

    return {"id": txn_id, "fraud_probability": prob, "risk_level": risk, **result}


@app.post("/transactions")
def create_transaction(txn: TransactionIn):
    row = txn.dict()
    _reject_if_duplicate(row)
    return _score_and_store(row)


@app.get("/transactions")
def list_transactions():
    conn = get_db()
    rows = conn.execute("SELECT * FROM transactions ORDER BY fraud_probability DESC, created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.patch("/transactions/{txn_id}")
def update_status(txn_id: int, update: StatusUpdate):
    conn = get_db()
    cur = conn.execute("UPDATE transactions SET status = ? WHERE id = ?", (update.status, txn_id))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(404, "Transaction not found")
    return {"id": txn_id, "status": update.status}


@app.post("/seed-demo-data")
def seed_demo_data():
    """Convenience endpoint: scores a batch of sample transactions from the
    held-out dataset so the dashboard has data to show immediately."""
    df = pd.read_csv(BASE_DIR.parent / "data" / "transactions.csv").sample(25, random_state=7)
    created = []
    for _, row in df.iterrows():
        txn = TransactionIn(**{f: row[f] for f in FEATURES})
        created.append(_score_and_store(txn.dict()))
    return {"created": len(created)}


@app.get("/health")
def health():
    return {"status": "ok"}
