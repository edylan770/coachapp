# TrainerOS client app (mobile)

Expo (React Native) app for clients: offline-first workout logging, check-in
submission, and a read-only program overview. Built in Phase 2 per
`PROJECT_SPEC.md` §7/§8.

## Run it

```sh
cd mobile
npm install
npx expo start        # then open in Expo Go / a dev build
```

Point the app at your API by editing `expo.extra.apiUrl` in `app.json`.
`http://localhost:8000` works for iOS simulators; for a physical device or
Android emulator use your machine's LAN IP (Android emulator: `http://10.0.2.2:8000`).

## How offline sync works

- The assigned program (`GET /me/program`) is cached in SQLite (`kv` table) so
  Today/Program work with no connection.
- Completing a workout writes a `WorkoutLogPayload` (client-generated UUIDs
  for the log and every set) into the local `local_logs` queue, then attempts
  a push.
- `POST /me/sync` is an idempotent batch upsert; results are per-item, so a
  rejected record is parked (with its error) without blocking the queue.
- A NetInfo listener re-pushes whenever connectivity returns; the Account tab
  shows pending count and offers manual sync.
- "Today" = the first non-rest program day without a local log (sequential
  model — day N of the program, not calendar-mapped).
- Check-ins intentionally require a connection (photos upload directly);
  the offline mandate in the spec applies to workout logging.

## Screens

- **Today** — next workout, prescribed sets/reps/load, per-set logging
  (weight/reps or seconds/RPE), rest timer, kg/lb toggle.
- **Program** — read-only block → week → day overview with logged ✓ marks.
- **Check-in** — weight, tape measurements, adherence sliders, up to 4 photos,
  free-text; idempotent submit.
- **Account** — identity, sync status, manual sync, logout.

Auth: sign in, or redeem the invite token your trainer shared (creates the
account via `POST /auth/accept-invite`). Tokens live in SecureStore; access
tokens auto-refresh.
