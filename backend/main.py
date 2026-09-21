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
import sqlite3
import json
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


class TransactionIn(BaseModel):
    distance_from_home: float
    distance_from_last_transaction: float
    ratio_to_median_purchase: float
    repeat_borrower: int
    used_chip_or_biometric: int
    used_pin_or_otp: int
    is_online_channel: int
    hour_of_day: float
    loan_amount: float


class StatusUpdate(BaseModel):
    status: str  # cleared | flagged


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


@app.post("/transactions")
def create_transaction(txn: TransactionIn):
    row = txn.dict()
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
         recommended_action, status, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            row["distance_from_home"], row["distance_from_last_transaction"],
            row["ratio_to_median_purchase"], row["repeat_borrower"],
            row["used_chip_or_biometric"], row["used_pin_or_otp"],
            row["is_online_channel"], row["hour_of_day"], row["loan_amount"],
            prob, risk, result["explanation"], result["recommended_action"],
            "pending", datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    txn_id = cur.lastrowid
    conn.close()

    return {"id": txn_id, "fraud_probability": prob, "risk_level": risk, **result}


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
        created.append(create_transaction(txn))
    return {"created": len(created)}


@app.get("/health")
def health():
    return {"status": "ok"}
