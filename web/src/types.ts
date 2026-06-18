// Mirrors the API's Pydantic schemas. Will move to @traineros/shared once the
// mobile app (Phase 2) consumes the same types.

export type UserRole = "trainer" | "client";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Trainer {
  id: string;
  display_name: string;
  business_name: string | null;
  bio: string | null;
  logo_url: string | null;
  settings: Record<string, unknown>;
  created_at: string;
}

export type ClientStatus = "invited" | "active" | "paused";

export interface Client {
  id: string;
  email: string;
  full_name: string;
  status: ClientStatus;
  has_account: boolean;
  invite_expires_at: string | null;
  created_at: string;
}

export interface ClientWithInvite extends Client {
  invite_token: string;
}

export interface Exercise {
  id: string;
  name: string;
  description: string | null;
  video_url: string | null;
  parent_exercise_id: string | null;
  is_custom: boolean;
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
  id?: string;
  exercise_id: string;
  sets: number;
  rep_scheme: RepScheme;
  load_scheme: LoadScheme | null;
  tempo: string | null;
  rest_seconds: number | null;
  notes: string | null;
}

export interface Day {
  id?: string;
  name: string | null;
  is_rest_day: boolean;
  notes: string | null;
  prescriptions: Prescription[];
}

export interface Week {
  id?: string;
  name: string | null;
  days: Day[];
}

export interface Block {
  id?: string;
  name: string;
  notes: string | null;
  weeks: Week[];
}

export interface Program {
  id: string;
  name: string;
  description: string | null;
  client_id: string | null;
  is_template: boolean;
  version: number;
  source_program_id: string | null;
  starts_on: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProgramDetail extends Program {
  blocks: Block[];
}
