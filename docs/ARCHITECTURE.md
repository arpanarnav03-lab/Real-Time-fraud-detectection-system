# Architecture

## What's built today (hackathon prototype, 4-hour scope)

```
┌─────────────┐      ┌──────────────────────────────┐
│   React     │─────▶│   FastAPI (single service)   │
│  Dashboard  │◀─────│  ┌─────────────────────────┐  │
└─────────────┘      │  │ XGBoost fraud scorer    │  │
                      │  └───────────┬─────────────┘  │
                      │              ▼                │
                      │  ┌─────────────────────────┐  │
                      │  │ LLM explainer (Claude)  │  │
                      │  │  + rule-based fallback  │  │
                      │  └───────────┬─────────────┘  │
                      │              ▼                │
                      │  ┌─────────────────────────┐  │
                      │  │      SQLite storage      │  │
                      │  └─────────────────────────┘  │
                      └──────────────────────────────┘
```

- **Frontend**: single-file React (CDN, no build step) + Tailwind
- **Backend**: one FastAPI service (API + AI layer consolidated for build speed)
- **ML model**: XGBoost, class-weighted for imbalance (fraud ~3% of transactions), ROC-AUC-optimized
- **Explanation layer**: Claude API call for human-readable fraud reasoning; falls back to a deterministic rule-based explanation if the API key is unset or the call fails — the system never breaks scoring due to an LLM outage
- **Storage**: SQLite (zero-setup, file-based)
- **Auth**: none (out of scope for the demo)

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
| Database | SQLite | PostgreSQL + pgvector | Setup overhead not worth it for a 4-hour build; pgvector would power semantic similarity search across historical fraud cases |
| Deployment | Local only | Render (API) + Vercel (frontend) + managed Postgres | Avoids deploy-config risk right before a live demo |
| AI layer | Direct Claude API call | AWS Bedrock, prompt templates, guardrails | Same underlying pattern, swap the client for a managed service |
| Auth | None | JWT sessions, domain-restricted signup | Out of scope for a scoring demo |
| Services | Consolidated (1 service) | Split API / AI / DB layers | Faster to build and debug as one service under time pressure |

## Design rationale

- **Class imbalance**: fraud is rare (~3%), so the model uses `scale_pos_weight` (functionally equivalent to SMOTE for this dataset) rather than naive accuracy optimization, and is evaluated on ROC-AUC / precision-recall rather than accuracy alone.
- **Explainability**: every score returns its top contributing features (via XGBoost feature importances) alongside the LLM's plain-English reasoning, so a human reviewer always has a "why," not just a number.
- **Graceful degradation**: the explanation layer never lets an LLM failure block a fraud decision — this mirrors the confidence-threshold fallback pattern used in earlier production systems this prototype builds on (semantic search with a rule-based fallback when confidence is low).
- **Human-in-the-loop**: every transaction lands in a review queue with clear/flag actions rather than fully automated blocking, matching the problem statement's emphasis on not compromising customer trust.
