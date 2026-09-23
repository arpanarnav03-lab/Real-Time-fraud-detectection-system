"""Embeds a transaction's features into a 384-dim vector for semantic
similarity search over historical fraud cases (pgvector).
"""
import os
import time
from datetime import datetime

# DIAGNOSTIC (deploy hang investigation): huggingface_hub's per-request
# timeouts default to 10s each, but that bounds a single request/chunk, not
# the overall download — a slow-but-not-dead connection can still stall well
# past that. Pin both explicitly so a genuinely hung connection fails fast
# instead of hanging indefinitely. Must be set before sentence_transformers
# (which imports huggingface_hub) is imported below.
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "15")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "15")

MODEL_NAME = "all-MiniLM-L6-v2"

# Loaded on first use rather than at import. Importing sentence_transformers
# pulls in torch (~215MB, ~10s) and constructing the model downloads ~90MB
# from the HF Hub when the cache is cold — doing that at import time blocks
# the process before uvicorn can bind $PORT, which is what stalled the Render
# deploy. Deferring it lets the service come up and pass its health check
# immediately; the first transaction scored pays the load cost instead.
_model = None


def _get_model():
    global _model
    if _model is None:
        print(f"[{datetime.utcnow().isoformat()}] embeddings: first use — loading SentenceTransformer('{MODEL_NAME}') (downloads ~90MB if not cached)...", flush=True)
        _t0 = time.monotonic()
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
        print(f"[{datetime.utcnow().isoformat()}] embeddings: SentenceTransformer ready (+{time.monotonic() - _t0:.1f}s)", flush=True)
    return _model


def transaction_to_text(row: dict) -> str:
    return (
        f"Loan amount {row['loan_amount']:.0f}. "
        f"Distance from home {row['distance_from_home']:.1f} km. "
        f"Distance from last transaction {row['distance_from_last_transaction']:.1f} km. "
        f"Ratio to median purchase {row['ratio_to_median_purchase']:.2f}. "
        f"Hour of day {row['hour_of_day']:.1f}. "
        f"Repeat borrower: {'yes' if row['repeat_borrower'] else 'no'}. "
        f"Used chip or biometric: {'yes' if row['used_chip_or_biometric'] else 'no'}. "
        f"Used PIN or OTP: {'yes' if row['used_pin_or_otp'] else 'no'}. "
        f"Online channel: {'yes' if row['is_online_channel'] else 'no'}."
    )


def embed_transaction(row: dict) -> list[float]:
    vector = _get_model().encode(transaction_to_text(row), normalize_embeddings=True)
    return vector.tolist()
