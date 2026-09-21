# Real-Time Fraud Detection and Prevention in Digital Lending Ecosystems

A prototype fraud detection system for digital lending: an XGBoost model scores
each transaction for fraud risk, an LLM layer (with a rule-based fallback)
explains *why*, and a review dashboard lets a human clear or flag the result.

Built for [Synchrony Hackathon] — see `docs/ARCHITECTURE.md` for what's built
today vs. the target production architecture.

## Quickstart

### 1. Database (Neon Postgres)

The backend stores transactions in Postgres via SQLAlchemy, hosted on
[Neon](https://neon.tech) (has a free tier).

1. Create a Neon project (or use an existing one).
2. In the Neon dashboard, open **Connect** and copy the **pooled** connection
   string. It looks like:
   ```
   postgresql://<user>:<password>@<endpoint-id>.<region>.aws.neon.tech/<dbname>?sslmode=require&channel_binding=require
   ```
3. Paste it into `DATABASE_URL` in your `.env` (see step 2 below) — keep the
   `sslmode=require` and `channel_binding=require` query params, they're
   required for Neon's pooled endpoint and are handled correctly by the
   `psycopg` (v3) driver this project uses.

No manual `pgvector` setup is needed — on startup the app runs
`CREATE EXTENSION IF NOT EXISTS vector;` and creates any missing tables
automatically.

### 2. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp ../.env.example .env
# edit .env: set DATABASE_URL (required, see step 1 above), and optionally
# ANTHROPIC_API_KEY to enable LLM explanations — without it, the system
# falls back to rule-based explanations automatically

# train the model (already included as fraud_model.joblib, but you can retrain)
python3 ../data/generate_data.py   # regenerate synthetic dataset if needed
python3 train_model.py             # trains and saves fraud_model.joblib

# run the API (loads .env into the shell first)
set -a && source .env && set +a
uvicorn main:app --reload --port 8000
```

API is now live at `http://localhost:8000`. Check `http://localhost:8000/health`.

### 3. Frontend

No build step needed — it's a single HTML file using React via CDN.

```bash
cd frontend
python3 -m http.server 3000
```

Open `http://localhost:3000` in your browser.

### 4. Try it

Click **"Load Demo Transactions"** on the dashboard to seed 25 scored
transactions from the synthetic dataset. Click any row to see the fraud
explanation and clear/flag it.

## How it works

1. A transaction (loan amount, distance from home, channel used, etc.) is
   submitted to `POST /transactions`.
2. The XGBoost model returns a fraud probability and risk level (low/medium/high).
3. The top contributing features are extracted from the model's feature importances.
4. An LLM call (Claude) turns the score + features into a plain-English
   explanation and recommended action. If the API key isn't set or the call
   fails, a rule-based fallback generates the explanation instead — scoring
   never breaks due to an LLM outage.
5. The result is stored and shown on the dashboard for human review.

## Project structure

```
fraud-detection-hackathon/
├── backend/
│   ├── main.py           # FastAPI app — endpoints, scoring
│   ├── database.py       # SQLAlchemy engine/session (Postgres via Neon)
│   ├── models.py         # ORM models: transactions, fraud_case_embeddings
│   ├── train_model.py    # trains the XGBoost fraud model
│   ├── llm_explain.py    # LLM explanation + rule-based fallback
│   ├── fraud_model.joblib
│   └── requirements.txt
├── frontend/
│   └── index.html        # single-file React dashboard
├── data/
│   ├── generate_data.py  # synthetic fraud dataset generator
│   └── transactions.csv
├── docs/
│   └── ARCHITECTURE.md   # prototype vs. production architecture
└── README.md
```

## API reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/transactions` | Score and store a new transaction |
| GET | `/transactions` | List all scored transactions |
| PATCH | `/transactions/{id}` | Update status (`cleared` / `flagged`) |
| POST | `/seed-demo-data` | Seed 25 sample transactions for the demo |
| GET | `/health` | Health check |

## Model performance

Trained on a 20,000-row synthetic transaction dataset (3% fraud rate),
XGBoost with `scale_pos_weight` for class imbalance, stratified 80/20 split.
See training output for ROC-AUC and classification report.

## Security notes

- No secrets are hardcoded — `ANTHROPIC_API_KEY` and `DATABASE_URL` are read
  from environment variables only, via `.env` (gitignored).
- Input validation via Pydantic models on all API endpoints.
- The Postgres connection uses `sslmode=require` and `channel_binding=require`
  as provided by Neon; don't strip these from `DATABASE_URL`.
