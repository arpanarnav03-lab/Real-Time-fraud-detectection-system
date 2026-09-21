"""
Fraud detection API. Single FastAPI service handling:
- transaction scoring (XGBoost)
- LLM explanation (with rule-based fallback)
- persistence (Postgres via SQLAlchemy)
- CRUD endpoints for the dashboard

Hackathon-scope note: consolidated into one service for build speed.
Target production architecture splits this into API / AI-layer / DB
layers per the full spec (see docs/ARCHITECTURE.md).
"""
import hashlib
import math
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

# xgboost's native lib must finish initializing its OpenMP runtime before
# torch (pulled in indirectly by sentence-transformers below) initializes
# its own — loading torch first causes a segfault from the two colliding.
import xgboost  # noqa: F401

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from database import Base, SessionLocal, engine
from embeddings import embed_transaction
from llm_explain import explain_transaction
import models

BASE_DIR = Path(__file__).parent
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
    return SessionLocal()


def init_db():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    # create_all only adds missing tables, not missing columns on tables that
    # already existed from before this column was added.
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS similar_cases JSON"))

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


def _find_similar_cases(db, embedding: list, k: int = 3) -> list:
    rows = (
        db.query(models.Transaction)
        .join(models.FraudCaseEmbedding, models.FraudCaseEmbedding.transaction_id == models.Transaction.id)
        .order_by(models.FraudCaseEmbedding.embedding.cosine_distance(embedding))
        .limit(k)
        .all()
    )
    return [
        {
            "transaction_id": t.id,
            "risk_level": t.risk_level,
            "fraud_probability": t.fraud_probability,
            "loan_amount": t.loan_amount,
        }
        for t in rows
    ]


def _score_and_store(row: dict) -> dict:
    X = pd.DataFrame([row])[FEATURES]
    prob = float(model.predict_proba(X)[0, 1])
    risk = risk_level_from_prob(prob)
    top_features = top_contributing_features(row)
    embedding = embed_transaction(row)

    db = get_db()
    similar_cases = _find_similar_cases(db, embedding)

    result = explain_transaction(prob, risk, top_features, similar_cases)

    txn_row = models.Transaction(
        distance_from_home=row["distance_from_home"],
        distance_from_last_transaction=row["distance_from_last_transaction"],
        ratio_to_median_purchase=row["ratio_to_median_purchase"],
        repeat_borrower=row["repeat_borrower"],
        used_chip_or_biometric=row["used_chip_or_biometric"],
        used_pin_or_otp=row["used_pin_or_otp"],
        is_online_channel=row["is_online_channel"],
        hour_of_day=row["hour_of_day"],
        loan_amount=row["loan_amount"],
        fraud_probability=prob,
        risk_level=risk,
        explanation=result["explanation"],
        recommended_action=result["recommended_action"],
        source=result["source"],
        similar_cases=similar_cases,
        status="pending",
        created_at=datetime.utcnow().isoformat(),
    )
    db.add(txn_row)
    db.commit()
    txn_id = txn_row.id

    db.add(models.FraudCaseEmbedding(transaction_id=txn_id, embedding=embedding))
    db.commit()
    db.close()

    return {"id": txn_id, "fraud_probability": prob, "risk_level": risk, "similar_cases": similar_cases, **result}


@app.post("/transactions")
def create_transaction(txn: TransactionIn):
    row = txn.dict()
    _reject_if_duplicate(row)
    return _score_and_store(row)


@app.get("/transactions")
def list_transactions():
    db = get_db()
    rows = (
        db.query(models.Transaction)
        .order_by(models.Transaction.fraud_probability.desc(), models.Transaction.created_at.desc())
        .all()
    )
    columns = [c.name for c in models.Transaction.__table__.columns]
    result = [{c: getattr(r, c) for c in columns} for r in rows]
    db.close()
    return result


@app.patch("/transactions/{txn_id}")
def update_status(txn_id: int, update: StatusUpdate):
    db = get_db()
    row = db.get(models.Transaction, txn_id)
    if row is None:
        db.close()
        raise HTTPException(404, "Transaction not found")
    row.status = update.status
    db.commit()
    db.close()
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
