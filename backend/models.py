"""ORM models for the Postgres-backed storage layer."""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    distance_from_home = Column(Float)
    distance_from_last_transaction = Column(Float)
    ratio_to_median_purchase = Column(Float)
    repeat_borrower = Column(Integer)
    used_chip_or_biometric = Column(Integer)
    used_pin_or_otp = Column(Integer)
    is_online_channel = Column(Integer)
    hour_of_day = Column(Float)
    loan_amount = Column(Float)
    fraud_probability = Column(Float)
    risk_level = Column(String)
    explanation = Column(String)
    recommended_action = Column(String)
    source = Column(String)
    status = Column(String, default="pending")
    created_at = Column(String)


class FraudCaseEmbedding(Base):
    __tablename__ = "fraud_case_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    embedding = Column(Vector(384))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
