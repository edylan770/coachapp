#!/usr/bin/env bash
set -euo pipefail

# Dev-friendly: migrate on start. In a real deployment, run migrations as a
# separate deploy step instead.
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
