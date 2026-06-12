import * as Crypto from "expo-crypto";
import { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Pressable, Text, View } from "react-native";

import { kvGet, kvSet, loggedDayIds, queueWorkoutLog } from "@/lib/db";
import {
  flattenDays,
  getCachedProgram,
  loadLabel,
  nextWorkout,
  refreshProgram,
  repLabel,
} from "@/lib/program";
import { syncNow } from "@/lib/sync";
import type {
  CachedProgram,
  Prescription,
  SetLogPayload,
  WorkoutLogPayload,
} from "@/lib/types";
import { Button, Card, colors, Field, Screen, Subtle, Title } from "@/lib/ui";

interface SetEntry {
  weight: string;
  reps: string;
  seconds: string;
  rpe: string;
  done: boolean;
}

function toNum(value: string): number | null {
  if (value.trim() === "") return null;
  const n = Number(value.replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

export default function TodayScreen() {
  const [cache, setCache] = useState<CachedProgram | null>(() => getCachedProgram());
  const [logged, setLogged] = useState<Set<string>>(() => new Set(loggedDayIds()));
  const [unit, setUnit] = useState<"kg" | "lb">(() =>
    kvGet("unit") === "lb" ? "lb" : "kg",
  );
  const [entries, setEntries] = useState<Record<string, SetEntry[]>>({});
  const [restLeft, setRestLeft] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const startedAtRef = useRef<string | null>(null);

  const flat = useMemo(() => (cache ? flattenDays(cache.program) : []), [cache]);
  const next = useMemo(() => nextWorkout(flat, logged), [flat, logged]);
  const exerciseName = useMemo(() => {
    const map = new Map((cache?.exercises ?? []).map((e) => [e.id, e.name]));
    return (id: string) => map.get(id) ?? "Exercise";
  }, [cache]);

  // Refresh the cached program when the screen mounts (best effort, offline-safe).
  useEffect(() => {
    void (async () => {
      try {
        setCache(await refreshProgram());
      } catch {
        // offline — keep the cache
      }
    })();
  }, []);

  // (Re)build the entry grid whenever the target day changes.
  const dayId = next?.day.id;
  useEffect(() => {
    if (!next) {
      setEntries({});
      return;
    }
    const initial: Record<string, SetEntry[]> = {};
    for (const rx of next.day.prescriptions) {
      initial[rx.id] = Array.from({ length: rx.sets }, () => ({
        weight: "",
        reps: rx.rep_scheme.type === "fixed" ? String(rx.rep_scheme.reps) : "",
        seconds: rx.rep_scheme.type === "duration" ? String(rx.rep_scheme.seconds) : "",
        rpe: "",
        done: false,
      }));
    }
    setEntries(initial);
    startedAtRef.current = null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dayId]);

  // Rest timer countdown.
  useEffect(() => {
    if (restLeft === null) return;
    if (restLeft <= 0) {
      setRestLeft(null);
      return;
    }
    const timer = setTimeout(() => setRestLeft((s) => (s === null ? null : s - 1)), 1000);
    return () => clearTimeout(timer);
  }, [restLeft]);

  const updateEntry = (rxId: string, index: number, patch: Partial<SetEntry>) => {
    startedAtRef.current ??= new Date().toISOString();
    setEntries((prev) => {
      const rows = prev[rxId]?.map((row, i) => (i === index ? { ...row, ...patch } : row));
      return rows ? { ...prev, [rxId]: rows } : prev;
    });
  };

  const toggleDone = (rx: Prescription, index: number) => {
    const wasDone = entries[rx.id]?.[index]?.done ?? false;
    updateEntry(rx.id, index, { done: !wasDone });
    if (!wasDone && rx.rest_seconds) setRestLeft(rx.rest_seconds);
  };

  const completeWorkout = () => {
    if (!next) return;
    const sets: SetLogPayload[] = [];
    let position = 0;
    for (const rx of next.day.prescriptions) {
      (entries[rx.id] ?? []).forEach((row, i) => {
        const touched =
          row.done || row.weight !== "" || row.rpe !== "" ||
          (rx.rep_scheme.type === "duration" ? row.seconds !== "" : row.reps !== "");
        if (!touched) return;
        sets.push({
          id: Crypto.randomUUID(),
          prescription_id: rx.id,
          exercise_id: rx.exercise_id,
          exercise_name: exerciseName(rx.exercise_id),
          position: position++,
          set_number: i + 1,
          weight: toNum(row.weight),
          weight_unit: toNum(row.weight) === null ? null : unit,
          reps: rx.rep_scheme.type === "duration" ? null : toNum(row.reps),
          duration_seconds: rx.rep_scheme.type === "duration" ? toNum(row.seconds) : null,
          rpe: toNum(row.rpe),
          is_completed: row.done,
          prescribed_snapshot: {
            sets: rx.sets,
            rep_scheme: rx.rep_scheme,
            load_scheme: rx.load_scheme,
            tempo: rx.tempo,
            rest_seconds: rx.rest_seconds,
          },
        });
      });
    }
    if (sets.length === 0) {
      Alert.alert("Nothing to save", "Log at least one set first.");
      return;
    }
    const log: WorkoutLogPayload = {
      id: Crypto.randomUUID(),
      program_day_id: next.day.id,
      workout_date: new Date().toISOString().slice(0, 10),
      notes: null,
      started_at: startedAtRef.current,
      completed_at: new Date().toISOString(),
      set_logs: sets,
    };
    queueWorkoutLog(log);
    setLogged(new Set(loggedDayIds()));
    setRestLeft(null);
    void syncNow().catch(() => {});
    Alert.alert("Workout saved", "Logged on this device — it syncs when you're online.");
  };

  const refresh = async () => {
    setRefreshing(true);
    try {
      setCache(await refreshProgram());
      setLogged(new Set(loggedDayIds()));
    } catch {
      Alert.alert("Offline", "Couldn't reach the server — showing the cached program.");
    } finally {
      setRefreshing(false);
    }
  };

  if (!cache) {
    return (
      <Screen>
        <Title>No program yet</Title>
        <Subtle>
          Your trainer hasn't assigned a program, or this device hasn't been online to fetch
          it.
        </Subtle>
        <Button title="Check again" onPress={() => void refresh()} busy={refreshing} />
      </Screen>
    );
  }

  if (!next) {
    return (
      <Screen>
        <Title>Program complete 🎉</Title>
        <Subtle>
          Every training day of "{cache.program.name}" has been logged. Your trainer will take
          it from here.
        </Subtle>
        <Button title="Refresh program" onPress={() => void refresh()} busy={refreshing} />
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <View style={{ flexShrink: 1 }}>
          <Title>{next.dayLabel}</Title>
          <Subtle>
            {next.blockName} · {next.weekLabel} · day {next.seq} of {flat.length}
          </Subtle>
        </View>
        <Button
          variant="ghost"
          title={unit.toUpperCase()}
          onPress={() => {
            const nextUnit = unit === "kg" ? "lb" : "kg";
            setUnit(nextUnit);
            kvSet("unit", nextUnit);
          }}
        />
      </View>

      {next.day.notes ? <Subtle>{next.day.notes}</Subtle> : null}

      {next.day.prescriptions.map((rx) => (
        <Card key={rx.id}>
          <Text style={{ color: colors.text, fontSize: 16, fontWeight: "600" }}>
            {exerciseName(rx.exercise_id)}
          </Text>
          <Subtle>
            {`${rx.sets} × ${repLabel(rx.rep_scheme)}`}
            {loadLabel(rx.load_scheme) ? ` @ ${loadLabel(rx.load_scheme)}` : ""}
            {rx.tempo ? ` · tempo ${rx.tempo}` : ""}
            {rx.rest_seconds ? ` · rest ${rx.rest_seconds}s` : ""}
          </Subtle>
          {rx.notes ? <Subtle>{rx.notes}</Subtle> : null}

          {(entries[rx.id] ?? []).map((row, i) => (
            <View
              key={i}
              style={{ flexDirection: "row", alignItems: "flex-end", gap: 8 }}
            >
              <Text style={{ color: colors.dim, width: 18, marginBottom: 10 }}>{i + 1}</Text>
              <View style={{ flex: 1 }}>
                <Field
                  label={`Weight (${unit})`}
                  keyboardType="decimal-pad"
                  value={row.weight}
                  onChangeText={(v) => updateEntry(rx.id, i, { weight: v })}
                />
              </View>
              <View style={{ flex: 1 }}>
                {rx.rep_scheme.type === "duration" ? (
                  <Field
                    label="Seconds"
                    keyboardType="number-pad"
                    value={row.seconds}
                    onChangeText={(v) => updateEntry(rx.id, i, { seconds: v })}
                  />
                ) : (
                  <Field
                    label="Reps"
                    keyboardType="number-pad"
                    value={row.reps}
                    onChangeText={(v) => updateEntry(rx.id, i, { reps: v })}
                  />
                )}
              </View>
              <View style={{ flex: 1 }}>
                <Field
                  label="RPE"
                  keyboardType="decimal-pad"
                  value={row.rpe}
                  onChangeText={(v) => updateEntry(rx.id, i, { rpe: v })}
                />
              </View>
              <Pressable
                onPress={() => toggleDone(rx, i)}
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 8,
                  borderWidth: 1,
                  borderColor: row.done ? colors.accent : colors.border,
                  backgroundColor: row.done ? colors.accentDark : "transparent",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Text style={{ color: row.done ? colors.accent : colors.dim }}>✓</Text>
              </Pressable>
            </View>
          ))}
        </Card>
      ))}

      {restLeft !== null ? (
        <Card style={{ borderColor: colors.accentDark }}>
          <View
            style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}
          >
            <Text style={{ color: colors.accent, fontSize: 18, fontWeight: "700" }}>
              Rest {Math.floor(restLeft / 60)}:{String(restLeft % 60).padStart(2, "0")}
            </Text>
            <Button variant="ghost" title="Skip" onPress={() => setRestLeft(null)} />
          </View>
        </Card>
      ) : null}

      <Button title="Complete workout" onPress={completeWorkout} />
      <Button variant="ghost" title="Refresh program" onPress={() => void refresh()} busy={refreshing} />
    </Screen>
  );
}
