// Mirrors the API's response/request schemas (subset the client app needs).

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export type RepScheme =
  | { type: "fixed"; reps: number }
  | { type: "range"; min: number; max: number }
  | { type: "amrap" }
  | { type: "duration"; seconds: number };

export type LoadScheme =
  | { type: "absolute"; weight: number; unit: "kg" | "lb" }
  | { type: "percent_1rm"; percent: number }
  | { type: "rpe"; rpe: number }
  | { type: "rir"; rir: number }
  | { type: "bodyweight" };

export interface Prescription {
  id: string;
  exercise_id: string;
  position: number;
  sets: number;
  rep_scheme: RepScheme;
  load_scheme: LoadScheme | null;
  tempo: string | null;
  rest_seconds: number | null;
  notes: string | null;
}

export interface Day {
  id: string;
  name: string | null;
  is_rest_day: boolean;
  notes: string | null;
  position: number;
  prescriptions: Prescription[];
}

export interface Week {
  id: string;
  name: string | null;
  position: number;
  days: Day[];
}

export interface Block {
  id: string;
  name: string;
  notes: string | null;
  position: number;
  weeks: Week[];
}

export interface ProgramDetail {
  id: string;
  name: string;
  description: string | null;
  starts_on: string | null;
  version: number;
  blocks: Block[];
}

export interface ExerciseLite {
  id: string;
  name: string;
  description: string | null;
  video_url: string | null;
}

export interface CachedProgram {
  program: ProgramDetail;
  exercises: ExerciseLite[];
}

// --- offline sync payloads (client-generated UUIDs, idempotent upsert) ---

export interface SetLogPayload {
  id: string;
  prescription_id: string | null;
  exercise_id: string | null;
  exercise_name: string;
  position: number;
  set_number: number;
  weight: number | null;
  weight_unit: "kg" | "lb" | null;
  reps: number | null;
  duration_seconds: number | null;
  rpe: number | null;
  is_completed: boolean;
  prescribed_snapshot: Record<string, unknown> | null;
}

export interface WorkoutLogPayload {
  id: string;
  program_day_id: string | null;
  workout_date: string;
  notes: string | null;
  started_at: string | null;
  completed_at: string | null;
  set_logs: SetLogPayload[];
}

export interface SyncResultItem {
  id: string;
  status: "created" | "updated" | "rejected";
  detail: string | null;
}

export interface SyncResponse {
  results: SyncResultItem[];
}

export interface Adherence {
  training: number | null;
  nutrition: number | null;
  sleep: number | null;
}

export interface CheckInOut {
  id: string;
  check_in_date: string;
  weight: number | null;
  weight_unit: string | null;
  photos: string[];
  notes: string | null;
}
