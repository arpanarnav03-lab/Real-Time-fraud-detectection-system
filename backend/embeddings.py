"""Embeds a transaction's features into a 384-dim vector for semantic
similarity search over historical fraud cases (pgvector).
"""
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")


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
    vector = _model.encode(transaction_to_text(row), normalize_embeddings=True)
    return vector.tolist()
