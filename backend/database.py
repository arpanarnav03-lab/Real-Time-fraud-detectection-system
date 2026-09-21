"""SQLAlchemy engine/session setup for the Postgres (Neon) database.

Storage wiring only — table definitions live in models.py, request/business
logic in main.py.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env and fill in your "
        "Neon Postgres connection string (see README for setup)."
    )

# Neon hands out plain postgresql:// URLs, which SQLAlchemy defaults to
# psycopg2. We want the psycopg (v3) driver, which passes sslmode and
# channel_binding through to libpq correctly — force that dialect here so
# .env can keep the connection string exactly as copied from Neon.
ENGINE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(ENGINE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 10})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
