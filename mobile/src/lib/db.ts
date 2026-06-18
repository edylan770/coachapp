// Local persistence: a tiny kv store (cached program, prefs) and the offline
// workout-log queue. Rows stay after sync (synced=1) so screens can show
// what's been logged without a network round-trip.

import * as SQLite from "expo-sqlite";

import type { WorkoutLogPayload } from "./types";

const db = SQLite.openDatabaseSync("traineros.db");

db.execSync(`
  PRAGMA journal_mode = WAL;
  CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS local_logs (
    id TEXT PRIMARY KEY,
    program_day_id TEXT,
    payload TEXT NOT NULL,
    synced INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    updated_at TEXT NOT NULL
  );
`);

export function kvGet(key: string): string | null {
  const row = db.getFirstSync<{ value: string }>("SELECT value FROM kv WHERE key = ?", [key]);
  return row?.value ?? null;
}

export function kvSet(key: string, value: string): void {
  db.runSync(
    "INSERT INTO kv(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
    [key, value],
  );
}

export function kvRemove(key: string): void {
  db.runSync("DELETE FROM kv WHERE key = ?", [key]);
}

export function queueWorkoutLog(payload: WorkoutLogPayload): void {
  db.runSync(
    `INSERT INTO local_logs(id, program_day_id, payload, synced, last_error, updated_at)
     VALUES(?, ?, ?, 0, NULL, ?)
     ON CONFLICT(id) DO UPDATE SET
       payload = excluded.payload, synced = 0, last_error = NULL, updated_at = excluded.updated_at`,
    [payload.id, payload.program_day_id, JSON.stringify(payload), new Date().toISOString()],
  );
}

export function pendingLogs(): WorkoutLogPayload[] {
  const rows = db.getAllSync<{ payload: string }>(
    "SELECT payload FROM local_logs WHERE synced = 0 ORDER BY updated_at",
  );
  return rows.map((row) => JSON.parse(row.payload) as WorkoutLogPayload);
}

export function pendingCount(): number {
  const row = db.getFirstSync<{ n: number }>(
    "SELECT COUNT(*) AS n FROM local_logs WHERE synced = 0",
  );
  return row?.n ?? 0;
}

export function markLogSynced(id: string): void {
  db.runSync("UPDATE local_logs SET synced = 1, last_error = NULL WHERE id = ?", [id]);
}

export function markLogRejected(id: string, error: string): void {
  // Rejected records are kept (synced = 2) for inspection instead of being
  // retried forever or silently dropped.
  db.runSync("UPDATE local_logs SET synced = 2, last_error = ? WHERE id = ?", [error, id]);
}

export function loggedDayIds(): string[] {
  const rows = db.getAllSync<{ program_day_id: string }>(
    "SELECT DISTINCT program_day_id FROM local_logs WHERE program_day_id IS NOT NULL AND synced IN (0, 1)",
  );
  return rows.map((row) => row.program_day_id);
}

export function clearAllLocal(): void {
  db.execSync("DELETE FROM local_logs; DELETE FROM kv;");
}
