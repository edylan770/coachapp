import os
from pathlib import Path

# Must be set before any app module is imported so the engine binds to the
# test database.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://traineros:traineros@127.0.0.1:5432/traineros_test"
)
# HS256 wants >= 32 bytes of key material.
os.environ.setdefault("JWT_SECRET", "test-secret-0123456789abcdef0123456789abcdef")

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from alembic import command  # noqa: E402

API_DIR = Path(__file__).resolve().parents[1]


def _ensure_test_database_exists() -> None:
    url = make_url(os.environ["DATABASE_URL"])
    maintenance = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", pool_pre_ping=True
    )
    with maintenance.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    maintenance.dispose()


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Recreates the test schema from migrations once per test session."""
    _ensure_test_database_exists()

    from app.db import engine

    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "alembic"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables(migrated_database):
    yield
    from app.db import engine

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE refresh_tokens, users CASCADE"))


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    from app.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
