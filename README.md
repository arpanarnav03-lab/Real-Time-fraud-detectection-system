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
# edit .env:
# - DATABASE_URL (required, see step 1 above)
# - JWT_SECRET (required — signs auth tokens). Generate one with:
#     python3 -c "import secrets; print(secrets.token_hex(32))"
# - ANTHROPIC_API_KEY (optional) to enable LLM explanations — without it,
#   the system falls back to rule-based explanations automatically

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

### 4. Tests

```bash
cd backend
source venv/bin/activate
set -a && source .env && set +a   # tests run against the real app and Neon DB
python3 -m pytest tests/ -v
```

Covers scoring (known high/low-risk inputs land in the right risk band),
the auth flow (signup/login, protected routes reject a missing/invalid
token), and the input-validation edge cases (out-of-range fields, duplicate
rapid submissions, non-finite floats, over-length passwords). There's no
separate test database — each test that needs a user signs up with a
freshly generated email, so re-running the suite is safe.

### 5. Try it

Sign up for an account on the login screen (any email/password, 8+ characters)
— all `/transactions` endpoints require a logged-in session. Once in, click
**"Load Demo Transactions"** on the dashboard to seed 25 scored transactions
from the synthetic dataset. Click any row to see the fraud explanation and
clear/flag it.

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
│   ├── auth.py           # password hashing (bcrypt) + JWT issue/verify
│   ├── database.py       # SQLAlchemy engine/session (Postgres via Neon)
│   ├── models.py         # ORM models: users, transactions, fraud_case_embeddings
│   ├── embeddings.py     # sentence-transformers embedding for similarity search
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

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/signup` | — | Create an account (email + password, 8+ chars), returns a JWT |
| POST | `/auth/login` | — | Log in, returns a JWT |
| POST | `/transactions` | Bearer token | Score and store a new transaction |
| GET | `/transactions` | Bearer token | List all scored transactions |
| PATCH | `/transactions/{id}` | Bearer token | Update status (`cleared` / `flagged`) |
| POST | `/seed-demo-data` | Bearer token | Seed 25 sample transactions for the demo |
| GET | `/health` | — | Health check |

`/transactions*` and `/seed-demo-data` require an `Authorization: Bearer <token>`
header, obtained from `/auth/login` or `/auth/signup`.

## Model performance

Trained on a 20,000-row synthetic transaction dataset (3% fraud rate),
XGBoost with `scale_pos_weight` for class imbalance, stratified 80/20 split.
See training output for ROC-AUC and classification report.

## Security notes

- No secrets are hardcoded — `ANTHROPIC_API_KEY`, `DATABASE_URL`, and
  `JWT_SECRET` are read from environment variables only, via `.env`
  (gitignored). The app refuses to start without `JWT_SECRET` set.
- Passwords are hashed with bcrypt before storage; plaintext passwords are
  never persisted, logged, or echoed back in a validation-error response
  (FastAPI's default behavior echoes the rejected value — redacted here for
  any field named `password`). Passwords over bcrypt's 72-byte limit are
  rejected with a 422 rather than crashing the hash/verify call.
- All `/transactions*` and `/seed-demo-data` endpoints require a valid JWT
  (`Authorization: Bearer <token>`), issued by `/auth/login` or `/auth/signup`
  and valid for 24 hours.
- Input validation via Pydantic models on all API endpoints.
- The Postgres connection uses `sslmode=require` and `channel_binding=require`
  as provided by Neon; don't strip these from `DATABASE_URL`.
