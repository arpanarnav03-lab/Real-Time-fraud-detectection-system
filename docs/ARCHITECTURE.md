# Architecture

## What's built today

![Component diagram: a Borrower or Reviewer signs in through the Review Client (AuthScreen.jsx, App.jsx, Dashboard.jsx, TransactionRow.jsx), which authenticates against and reads/updates the API and Auth layer (FastAPI Service in main.py, JWT Authentication in auth.py). The Scoring Orchestrator in main.py creates an embedding vector and predicts risk via Detection Intelligence (embeddings.py, the XGBoost model, llm_explain.py's explanation engine with its rule-based fallback calling the Groq LLM), then builds records, finds similar cases, and stores results via the Persistence layer (models.py, database.py) backed by Neon Postgres, seeded from the demo transactions.csv dataset.](architecture.png)

- **Frontend**: React + Vite (Tailwind still via CDN `<script>` tag, no Tailwind build step) — see `frontend/`
- **Backend**: one FastAPI service (API + AI layer consolidated for build speed) — see `backend/`
- **Auth**: email/password signup and login, bcrypt-hashed passwords, JWT bearer tokens (24h expiry). All `/transactions*` and `/seed-demo-data` endpoints require a valid token.
- **ML model**: XGBoost, class-weighted for imbalance (fraud ~3% of transactions), ROC-AUC-optimized
- **Semantic similarity**: each transaction is embedded (`sentence-transformers`, 384-dim) and stored in `fraud_case_embeddings`; scoring a new transaction retrieves its top-3 nearest historical cases via pgvector cosine distance, and that context is passed into the explanation prompt
- **Explanation layer**: Groq API call (Llama 3.3 70B, OpenAI-compatible client) for human-readable fraud reasoning, informed by the similar-case history above; falls back to a deterministic rule-based explanation if the API key is unset or the call fails — the system never breaks scoring due to an LLM outage
- **Storage**: PostgreSQL via SQLAlchemy, hosted on Neon, with the `pgvector` extension enabled and in active use for similarity search
- **Deployment**: config is ready (`render.yaml` for the backend, `frontend/vercel.json` for the frontend) but nothing is deployed yet — see the README's Deployment section

## Target production architecture (per problem statement spec)

```
React (Frontend) → Spring Boot / API Gateway → PostgreSQL + pgvector
                          │
                          ▼
                  AWS Bedrock (LLM) + embedding model
                  (prompt templates, guardrails, agent framework)
                          │
                          ▼
              AWS Cloud Layer (deploy, secure storage, monitoring)
                          │
                          ▼
        Security Layer (auth/authz, input validation, secret mgmt)
```

Key differences from today's build, and why they're deferred:

| Component | Prototype | Production target | Why deferred |
|---|---|---|---|
| Deployment | Config ready, not live | Render (API) + Vercel (frontend) + managed Postgres | No live URL needed until demo day; config is committed and reviewed |
| AI layer | Direct Groq API call | AWS Bedrock, prompt templates, guardrails | Same underlying pattern, swap the client for a managed service |
| Auth | Email/password + JWT | JWT sessions, domain-restricted signup | Domain restriction and session refresh are out of scope for a scoring demo |
| Services | Consolidated (1 service) | Split API / AI / DB layers | Faster to build and debug as one service under time pressure |

## Design rationale

- **Class imbalance**: fraud is rare (~3%), so the model uses `scale_pos_weight` (functionally equivalent to SMOTE for this dataset) rather than naive accuracy optimization, and is evaluated on ROC-AUC / precision-recall rather than accuracy alone.
- **Explainability**: every score returns its top contributing features (via XGBoost feature importances) alongside the LLM's plain-English reasoning, so a human reviewer always has a "why," not just a number.
- **Graceful degradation**: the explanation layer never lets an LLM failure block a fraud decision — this mirrors the confidence-threshold fallback pattern used in earlier production systems this prototype builds on (semantic search with a rule-based fallback when confidence is low).
- **Human-in-the-loop**: every transaction lands in a review queue with clear/flag actions rather than fully automated blocking, matching the problem statement's emphasis on not compromising customer trust.
