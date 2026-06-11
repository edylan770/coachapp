# TrainerOS (working name) — Project Spec & Build Prompt

You are building a production-grade, subscription-based coaching platform for fitness trainers (initial cohort: bodybuilding coaches, but the data model must be niche-agnostic). The core differentiator: a per-trainer AI layer powered ONLY by that trainer's own data (RAG over their proprietary corpus), which drafts client-facing content for trainer approval. The AI amplifies the trainer's methodology and voice — it never gives generic advice from general training data.

Work incrementally. Do not scaffold everything at once. Follow the phase order below, write migrations and tests as you go, and ask before making architectural decisions not covered here.

---

## 1. Product Overview

**Users:** Trainers (web dashboard) and their Clients (mobile app).

**Core v1 loop (everything else hangs off this):**
1. Trainer onboards: imports existing program spreadsheets/docs + completes an AI "methodology interview"
2. Trainer builds a training program and assigns it to a client
3. Client logs workouts in the mobile app (must work offline)
4. Client submits a weekly check-in (metrics, photos, adherence, free-text)
5. AI drafts a check-in response and any program adjustments, grounded ONLY in this trainer's corpus + this client's structured history
6. Trainer approves/edits/rejects the draft; the edit diff is captured as training signal
7. Client receives the response

**Explicitly OUT of v1 scope:** payments/billing, video form review, habit tracking, meal-plan builder (beyond template placeholders), client-facing autonomous AI chat, social features. Leave clean extension points; do not build them.

---

## 2. Stack

- **Monorepo** (e.g., Turborepo or simple workspace layout): `api/`, `web/`, `mobile/`, `packages/shared/`
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x + Alembic migrations, Pydantic v2
- **Database:** PostgreSQL 16 with `pgvector` extension (no separate vector DB at this scale)
- **Trainer dashboard:** React + TypeScript + Vite, Tailwind, TanStack Query
- **Client app:** React Native via Expo, TypeScript. Offline-first workout logging (local SQLite queue, sync on reconnect). Push notifications via Expo.
- **AI:** Anthropic API (Claude) for generation; a configurable embedding model behind an interface (so it can be swapped). All AI calls server-side only.
- **Auth:** email/password + OAuth-ready. JWT access/refresh. Two roles: `trainer`, `client`. Clients are invited by trainers (no public client signup).
- **Infra assumptions:** Dockerized services, `.env` config, secrets never committed. Object storage interface (S3-compatible) for photos/docs.

---

## 3. Data Model (core tables)

Design for niche-agnosticism: powerlifting %-based waves, bodybuilding hypertrophy blocks, and general fitness must all fit the same primitives.

- `trainers` — profile, branding, settings
- `trainer_ai_settings` — per-feature AI autonomy flags (see §6). Default: everything draft-only.
- `clients` — belongs to one trainer; status (invited/active/paused)
- `exercises` — global library + per-trainer custom exercises (trainer-scoped overrides)
- `programs` — belongs to trainer, assigned to client; versioned
- `program_blocks` → `program_weeks` → `program_days` → `prescriptions`
  - `prescriptions`: exercise_id, sets, rep scheme (range or fixed), load scheme (absolute / %1RM / RPE / RIR), tempo, rest, notes. Use a flexible but typed structure (JSONB with Pydantic validation), not free text.
- `workout_logs` + `set_logs` — actuals vs prescribed; client-entered; offline-sync friendly (client-generated UUIDs, idempotent upsert)
- `check_ins` — scheduled cadence per client; payload: weight, measurements, photos (object storage refs), adherence ratings, free-text
- `messages` — trainer↔client thread
- `metrics` — time-series (bodyweight, e1RMs, adherence %) for trend display and AI context
- `corpus_documents` — trainer-owned source docs (uploads, interview answers, sent replies, written programs)
- `corpus_chunks` — chunked text + embedding (pgvector), metadata (source type, date)
- `ai_drafts` — type (check_in_reply / program_adjustment), input context snapshot, generated text, retrieval citations, status (pending/approved/edited/rejected), final_text, edit_diff
- `nutrition_templates` — trainer-authored templates only. UI language must say "template/guidance", never "prescribed meal plan" (regulatory framing).

---

## 4. RAG / AI Layer — the core differentiator

**Hard multi-tenancy is non-negotiable.** Every corpus query MUST be filtered by `trainer_id` at the query layer (enforced in the repository/service code, not by prompt instructions). Write a test that proves Trainer A's retrieval can never return Trainer B's chunks. Cross-trainer leakage is a business-ending bug.

**Hybrid retrieval, not embeddings-only:**
- Structured facts (client's program, logged numbers, metric trends, adherence) come from SQL queries — deterministic, never from embeddings.
- Semantic retrieval over `corpus_chunks` supplies the trainer's philosophy, voice, and decision rationale.
- Fuse both into the generation context. (Reciprocal rank fusion if multiple retrievers; keep the retriever behind a clean interface.)

**Corpus ingestion (trainer onboarding):**
1. **Spreadsheet/doc import:** parse xlsx/csv/pdf program files. Map recognizable structures into `programs`/`prescriptions` where possible; everything else becomes corpus text. Show the trainer a review/confirm step — never silently guess.
2. **Methodology interview:** a guided conversational flow (10–20 questions) — e.g., "How do you handle a client who misses two sessions?", "Describe your deload philosophy", "Write a sample check-in reply in your voice." Answers are stored as corpus documents tagged by topic.
3. **Continuous learning:** every program the trainer writes and every check-in reply they SEND (final text, post-edit) is appended to the corpus. The AI gets more like this trainer over time.

**Generation rules:**
- System prompt instructs the model to use ONLY the provided trainer corpus + client structured data; if the corpus doesn't cover a question, the draft must say so and defer to the trainer rather than fall back on general knowledge.
- Every draft stores its retrieval citations (which chunks were used) for trainer transparency ("why did it say this?").
- Capture `edit_diff` whenever a trainer modifies a draft before sending. Store it from day one even though v1 does nothing with it yet.

**Safety rails:** drafts touching injury, pain, medical conditions, or rapid weight loss get flagged for mandatory trainer review (no autonomy setting can bypass), with a visible warning to the trainer.

---

## 5. Trainer Dashboard (web) — v1 screens

1. Onboarding wizard: corpus import → methodology interview → invite first client
2. Client roster with status indicators (pending check-in, AI draft awaiting review, adherence flags)
3. Program builder: block/week/day/prescription editor; template save/duplicate; assign to client
4. Check-in review queue: client submission side-by-side with AI draft; approve / edit / reject; one-tap send
5. Client detail: metric trends, program history, message thread
6. AI settings: per-feature autonomy toggles + corpus manager (view/add/remove documents)

## 6. AI Autonomy Settings (per trainer)

Each AI feature has an independent setting: **off / draft-for-approval / auto-send**. v1 defaults everything to draft-for-approval; auto-send exists in the schema and settings UI but can ship disabled behind a feature flag. Safety-flagged content is always draft-only regardless of settings.

## 7. Client App (mobile) — v1 screens

1. Today's workout: prescription display, set logging (weight/reps/RPE), rest timer. **Must work fully offline; sync queue on reconnect.**
2. Check-in flow: metrics entry, photo upload, adherence sliders, free-text
3. Program overview (read-only)
4. Messages with trainer
5. Simple progress charts (bodyweight, key lifts)

---

## 8. Build Order (do not deviate)

1. **Phase 0:** monorepo scaffold, Docker compose (Postgres+pgvector, API), auth, migrations baseline
2. **Phase 1:** core schema + CRUD APIs (trainers, clients, exercises, programs, prescriptions) + program builder UI
3. **Phase 2:** client mobile app — workout logging with offline sync; check-in submission
4. **Phase 3:** corpus ingestion (upload + parse + chunk + embed), methodology interview flow
5. **Phase 4:** AI draft pipeline (hybrid retrieval → generation → citations), check-in review queue, edit-diff capture
6. **Phase 5:** messaging, metrics/trends, AI settings UI, polish, error handling, rate limiting

At each phase: Alembic migration, API tests (pytest), and a short README note on how to run it. Prefer boring, maintainable code over cleverness. Flag any place where you'd otherwise invent product behavior not specified here.
