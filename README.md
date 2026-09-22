# Real-Time Fraud Detection and Prevention in Digital Lending Ecosystems

A prototype fraud detection system for digital lending: an XGBoost model scores
each transaction for fraud risk, an LLM layer (with a rule-based fallback)
explains *why*, and a review dashboard lets a human clear or flag the result.

Built for [Synchrony Hackathon] — see `docs/ARCHITECTURE.md` for what's built
today vs. the target production architecture.

## Architecture

![Component diagram: a Borrower or Reviewer signs in through the Review Client (AuthScreen.jsx, App.jsx, Dashboard.jsx, TransactionRow.jsx), which authenticates against and reads/updates the API and Auth layer (FastAPI Service in main.py, JWT Authentication in auth.py). The Scoring Orchestrator in main.py creates an embedding vector and predicts risk via Detection Intelligence (embeddings.py, the XGBoost model, llm_explain.py's explanation engine with its rule-based fallback calling the Groq LLM), then builds records, finds similar cases, and stores results via the Persistence layer (models.py, database.py) backed by Neon Postgres, seeded from the demo transactions.csv dataset.](docs/architecture.png)

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
# - GROQ_API_KEY (optional) to enable LLM explanations — without it,
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

A Vite + React project. Tailwind is still loaded via the CDN `<script>` tag
in `index.html` (no Tailwind build step) — only React/JSX go through Vite.

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser (the dev server is configured
to use port 3000 to match the previous setup).

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
4. An LLM call (Groq, Llama 3.3 70B) turns the score + features into a
   plain-English explanation and recommended action. If the API key isn't
   set or the call fails, a rule-based fallback generates the explanation
   instead — scoring never breaks due to an LLM outage.
5. The result is stored and shown on the dashboard for human review.

## Project structure

```
fraud-detection-hackathon/
├── render.yaml            # Render Blueprint — backend deployment config
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
│   ├── index.html         # Vite entry HTML — Tailwind CDN tag lives here
│   ├── vite.config.js
│   ├── package.json
│   ├── vercel.json        # frontend deployment config (Vite preset)
│   └── src/
│       ├── main.jsx       # mounts <App /> into #root
│       ├── App.jsx        # top-level auth gate (login/signup vs. dashboard)
│       ├── AuthScreen.jsx
│       ├── Dashboard.jsx
│       ├── TransactionRow.jsx
│       ├── StatCard.jsx
│       ├── NewTransactionPanel.jsx
│       ├── NumberField.jsx
│       ├── ToggleField.jsx
│       ├── constants.js   # API_BASE, RISK_STYLES, form presets
│       └── utils.js       # shared error-message helpers
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

## Deployment

Config files are in the repo and ready to go, but **nothing is deployed
yet** — this section is a reference for when you are ready.

### Environment variables

Set these on whichever platform hosts the backend (e.g. Render). Never put
real values in `.env.example` or any committed file.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Neon Postgres pooled connection string (`sslmode=require&channel_binding=require`) |
| `JWT_SECRET` | Yes | Signs/verifies auth tokens. Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `GROQ_API_KEY` | No | Enables LLM explanations (Groq, Llama 3.3 70B); without it, the rule-based fallback is used |

### Backend → Render

[render.yaml](render.yaml) is a Blueprint targeting the free plan:
`rootDir: backend`, installs `requirements.txt`, runs
`uvicorn main:app --host 0.0.0.0 --port $PORT`, and checks `/health`.

1. In the Render dashboard: **New → Blueprint**, point it at this repo.
2. Render reads `render.yaml` and prompts for the three env vars above
   (they're marked `sync: false` in the file, so they're never read from —
   or written to — the repo).
3. First deploy will take a few minutes: it installs `xgboost`,
   `sentence-transformers` (pulls in torch), and `psycopg[binary]`.

**Free-tier caveats worth knowing before you rely on it for a demo:**
- The service spins down after 15 minutes idle and cold-starts (tens of
  seconds — it has to reload the XGBoost model and the sentence-transformers
  embedding model) on the next request.
- Free tier is memory-constrained (512 MB); XGBoost + torch loaded together
  at startup are not tiny. If the service OOMs on boot, that's the first
  thing to check — upgrading the plan is the fix, not a code change.

### Frontend → Vercel

The frontend is a Vite project with a build step (`npm run build` →
`frontend/dist`). [frontend/vercel.json](frontend/vercel.json) declares
`"framework": "vite"`, which Vite would also auto-detect on its own from
`vite.config.js` + `package.json`.

1. Import this repo in the Vercel dashboard, then set **Root Directory** to
   `frontend` in the project's Build & Deployment settings — this is a
   per-project dashboard setting for monorepos, not something a repo-root
   config file can express. Vercel then runs `npm install && npm run build`
   and serves `dist/` automatically; no other settings are needed.
2. **Before deploying**, update `API_BASE` in `frontend/src/constants.js`
   from `http://localhost:8000` to your deployed Render backend's URL.

### After both are deployed

- Tighten CORS: `backend/main.py` currently sets `allow_origins=["*"]`,
  which is fine for local dev but should be narrowed to your deployed
  frontend's exact origin (e.g. `https://your-app.vercel.app`) once you
  know it.
- Re-run the checklist above (`API_BASE`, CORS) any time the deployed
  frontend or backend URL changes.

## Security notes

- No secrets are hardcoded — `GROQ_API_KEY`, `DATABASE_URL`, and
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
