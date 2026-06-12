import { api, ApiError } from "./api";
import { kvGet, kvRemove, kvSet } from "./db";
import type { CachedProgram, Day, LoadScheme, ProgramDetail, RepScheme } from "./types";

const CACHE_KEY = "program.cache";

export function getCachedProgram(): CachedProgram | null {
  const raw = kvGet(CACHE_KEY);
  if (raw === null) return null;
  try {
    return JSON.parse(raw) as CachedProgram;
  } catch {
    return null;
  }
}

/** Fetches the assigned program and caches it for offline use. */
export async function refreshProgram(): Promise<CachedProgram | null> {
  try {
    const data = await api<CachedProgram>("/me/program");
    kvSet(CACHE_KEY, JSON.stringify(data));
    return data;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      kvRemove(CACHE_KEY);
      return null;
    }
    throw error;
  }
}

export interface FlatDay {
  seq: number; // 1-based position in the overall sequence
  blockName: string;
  weekLabel: string;
  dayLabel: string;
  day: Day;
}

/** The program as one ordered sequence of days (offline "today" logic). */
export function flattenDays(program: ProgramDetail): FlatDay[] {
  const flat: FlatDay[] = [];
  let seq = 0;
  for (const block of program.blocks) {
    for (const [weekIndex, week] of block.weeks.entries()) {
      for (const [dayIndex, day] of week.days.entries()) {
        seq += 1;
        flat.push({
          seq,
          blockName: block.name,
          weekLabel: week.name ?? `Week ${weekIndex + 1}`,
          dayLabel: day.name ?? `Day ${dayIndex + 1}`,
          day,
        });
      }
    }
  }
  return flat;
}

/** Next training day = first non-rest day without a local log. */
export function nextWorkout(flat: FlatDay[], loggedDayIds: Set<string>): FlatDay | null {
  for (const entry of flat) {
    if (entry.day.is_rest_day) continue;
    if (!loggedDayIds.has(entry.day.id)) return entry;
  }
  return null;
}

export function repLabel(scheme: RepScheme): string {
  switch (scheme.type) {
    case "fixed":
      return `${scheme.reps} reps`;
    case "range":
      return `${scheme.min}–${scheme.max} reps`;
    case "amrap":
      return "AMRAP";
    case "duration":
      return `${scheme.seconds}s`;
  }
}

export function loadLabel(scheme: LoadScheme | null): string | null {
  if (scheme === null) return null;
  switch (scheme.type) {
    case "absolute":
      return `${scheme.weight} ${scheme.unit}`;
    case "percent_1rm":
      return `${scheme.percent}% 1RM`;
    case "rpe":
      return `RPE ${scheme.rpe}`;
    case "rir":
      return `${scheme.rir} RIR`;
    case "bodyweight":
      return "bodyweight";
  }
}

export function prescriptionSummary(sets: number, rep: RepScheme, load: LoadScheme | null): string {
  const loadPart = loadLabel(load);
  return `${sets} × ${repLabel(rep)}${loadPart ? ` @ ${loadPart}` : ""}`;
}
