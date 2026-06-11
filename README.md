# TrainerOS

Subscription coaching platform for fitness trainers: trainers run their roster
from a web dashboard, clients log workouts and check-ins from a mobile app, and
a per-trainer AI layer (RAG over the trainer's own corpus) drafts client-facing
content for trainer approval. Full product spec: [PROJECT_SPEC.md](PROJECT_SPEC.md).

## Repo layout

| Path | What |
|---|---|
| `api/` | FastAPI backend — Python 3.12, SQLAlchemy 2, Alembic, Postgres 16 + pgvector |
| `web/` | Trainer dashboard — React 19, TypeScript, Vite, Tailwind v4, TanStack Query |
| `mobile/` | Client app — Expo/React Native (placeholder until Phase 2) |
| `packages/shared/` | Shared TypeScript types for web + mobile |

## Phase status

- [x] **Phase 0** — monorepo scaffold, docker compose (Postgres+pgvector, API), email/password auth (JWT access + rotating refresh tokens), Alembic baseline migration, pytest suite
- [ ] Phase 1 — core schema + CRUD (trainers, clients, exercises, programs, prescriptions) + program builder UI
- [ ] Phase 2 — mobile app: offline workout logging, check-in submission
- [ ] Phase 3 — corpus ingestion + methodology interview
- [ ] Phase 4 — AI draft pipeline (hybrid retrieval, citations, review queue, edit-diff)
- [ ] Phase 5 — messaging, metrics/trends, AI settings UI, polish

## Run with docker

```sh
cp .env.example .env   # then set a real JWT_SECRET
docker compose up --build
```

API at <http://localhost:8000> (OpenAPI docs at `/docs`). Migrations run
automatically on container start.

## Run locally (dev)

```sh
# 1. Database
docker compose up -d db

# 2. API
cd api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# 3. Web dashboard (separate shell, repo root)
npm install
npm run dev:web        # http://localhost:5173, proxies /api → localhost:8000
```

## Tests & lint

```sh
cd api
pytest                 # needs Postgres running; uses the traineros_test
                       # database (created automatically if missing)
ruff check app tests alembic
```

Test DB override: `DATABASE_URL=postgresql+psycopg://...` before `pytest`.

## Auth model (Phase 0)

- Public registration creates **trainers only** — clients are invited by their
  trainer (Phase 1); there is no public client signup.
- Short-lived JWT access tokens (15 min) + opaque refresh tokens stored hashed
  in Postgres. Refresh tokens rotate on every use; reuse of a rotated token
  revokes all of that user's active tokens. Logout revokes the refresh token.
- `users.password_hash` is nullable so OAuth-only identities can be added
  later without a schema change.

## Decisions made in Phase 0 (flag if you'd choose differently)

- **Sync SQLAlchemy + psycopg3** rather than async — boring and simple at this
  scale; FastAPI runs sync endpoints in a threadpool.
- **npm workspaces** rather than Turborepo — no task graph needed yet.
- **Opaque DB-backed refresh tokens** rather than JWT refresh tokens — server
  revocation beats statelessness for auth.
- **pgvector extension enabled in the baseline migration** so every
  environment is vector-ready before Phase 3 (needs superuser; the docker
  image's default role qualifies).
