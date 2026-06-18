import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, errorMessage } from "../api";
import type {
  Block,
  Client,
  Exercise,
  LoadScheme,
  Prescription,
  Program,
  ProgramDetail,
  RepScheme,
} from "../types";

function moveItem<T>(items: T[], from: number, to: number): void {
  if (to < 0 || to >= items.length) return;
  const [item] = items.splice(from, 1);
  items.splice(to, 0, item);
}

function MoveButtons({ onUp, onDown, onRemove }: { onUp: () => void; onDown: () => void; onRemove: () => void }) {
  return (
    <div className="flex shrink-0 gap-1">
      <button type="button" className="btn-ghost px-2" title="Move up" onClick={onUp}>
        ↑
      </button>
      <button type="button" className="btn-ghost px-2" title="Move down" onClick={onDown}>
        ↓
      </button>
      <button type="button" className="btn-danger px-2" title="Remove" onClick={onRemove}>
        ✕
      </button>
    </div>
  );
}

function RepSchemeEditor({ value, onChange }: { value: RepScheme; onChange: (v: RepScheme) => void }) {
  return (
    <div className="flex items-center gap-1">
      <select
        className="select"
        value={value.type}
        onChange={(e) => {
          const type = e.target.value as RepScheme["type"];
          if (type === "fixed") onChange({ type, reps: 8 });
          else if (type === "range") onChange({ type, min: 8, max: 12 });
          else if (type === "duration") onChange({ type, seconds: 45 });
          else onChange({ type: "amrap" });
        }}
      >
        <option value="fixed">Reps</option>
        <option value="range">Rep range</option>
        <option value="amrap">AMRAP</option>
        <option value="duration">Seconds</option>
      </select>
      {value.type === "fixed" && (
        <input
          type="number"
          min={1}
          className="input w-16"
          value={value.reps}
          onChange={(e) => onChange({ ...value, reps: Number(e.target.value) })}
        />
      )}
      {value.type === "range" && (
        <>
          <input
            type="number"
            min={1}
            className="input w-14"
            value={value.min}
            onChange={(e) => onChange({ ...value, min: Number(e.target.value) })}
          />
          <span className="text-slate-500">–</span>
          <input
            type="number"
            min={1}
            className="input w-14"
            value={value.max}
            onChange={(e) => onChange({ ...value, max: Number(e.target.value) })}
          />
        </>
      )}
      {value.type === "duration" && (
        <input
          type="number"
          min={1}
          className="input w-20"
          value={value.seconds}
          onChange={(e) => onChange({ ...value, seconds: Number(e.target.value) })}
        />
      )}
    </div>
  );
}

function LoadSchemeEditor({ value, onChange }: { value: LoadScheme | null; onChange: (v: LoadScheme | null) => void }) {
  const type = value?.type ?? "none";
  return (
    <div className="flex items-center gap-1">
      <select
        className="select"
        value={type}
        onChange={(e) => {
          const next = e.target.value;
          if (next === "none") onChange(null);
          else if (next === "absolute") onChange({ type: "absolute", weight: 100, unit: "kg" });
          else if (next === "percent_1rm") onChange({ type: "percent_1rm", percent: 75 });
          else if (next === "rpe") onChange({ type: "rpe", rpe: 8 });
          else if (next === "rir") onChange({ type: "rir", rir: 2 });
          else onChange({ type: "bodyweight" });
        }}
      >
        <option value="none">No load</option>
        <option value="absolute">Weight</option>
        <option value="percent_1rm">%1RM</option>
        <option value="rpe">RPE</option>
        <option value="rir">RIR</option>
        <option value="bodyweight">Bodyweight</option>
      </select>
      {value?.type === "absolute" && (
        <>
          <input
            type="number"
            min={0}
            className="input w-20"
            value={value.weight}
            onChange={(e) => onChange({ ...value, weight: Number(e.target.value) })}
          />
          <select
            className="select"
            value={value.unit}
            onChange={(e) => onChange({ ...value, unit: e.target.value as "kg" | "lb" })}
          >
            <option value="kg">kg</option>
            <option value="lb">lb</option>
          </select>
        </>
      )}
      {value?.type === "percent_1rm" && (
        <input
          type="number"
          min={1}
          max={200}
          className="input w-16"
          value={value.percent}
          onChange={(e) => onChange({ ...value, percent: Number(e.target.value) })}
        />
      )}
      {value?.type === "rpe" && (
        <input
          type="number"
          min={1}
          max={10}
          step={0.5}
          className="input w-16"
          value={value.rpe}
          onChange={(e) => onChange({ ...value, rpe: Number(e.target.value) })}
        />
      )}
      {value?.type === "rir" && (
        <input
          type="number"
          min={0}
          max={10}
          className="input w-16"
          value={value.rir}
          onChange={(e) => onChange({ ...value, rir: Number(e.target.value) })}
        />
      )}
    </div>
  );
}

function PrescriptionRow({
  prescription,
  exercises,
  onChange,
  onUp,
  onDown,
  onRemove,
}: {
  prescription: Prescription;
  exercises: Exercise[];
  onChange: (mutator: (p: Prescription) => void) => void;
  onUp: () => void;
  onDown: () => void;
  onRemove: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-md border border-slate-800 bg-slate-950/60 p-2">
      <select
        className="select min-w-44"
        value={prescription.exercise_id}
        onChange={(e) => onChange((p) => (p.exercise_id = e.target.value))}
      >
        {exercises.map((ex) => (
          <option key={ex.id} value={ex.id}>
            {ex.name}
            {ex.is_custom ? " *" : ""}
          </option>
        ))}
      </select>
      <label className="flex items-center gap-1 text-xs text-slate-400">
        Sets
        <input
          type="number"
          min={1}
          max={100}
          className="input w-14"
          value={prescription.sets}
          onChange={(e) => onChange((p) => (p.sets = Number(e.target.value)))}
        />
      </label>
      <RepSchemeEditor
        value={prescription.rep_scheme}
        onChange={(v) => onChange((p) => (p.rep_scheme = v))}
      />
      <LoadSchemeEditor
        value={prescription.load_scheme}
        onChange={(v) => onChange((p) => (p.load_scheme = v))}
      />
      <input
        className="input w-20"
        placeholder="Tempo"
        value={prescription.tempo ?? ""}
        onChange={(e) => onChange((p) => (p.tempo = e.target.value || null))}
      />
      <label className="flex items-center gap-1 text-xs text-slate-400">
        Rest&nbsp;s
        <input
          type="number"
          min={0}
          max={3600}
          className="input w-18"
          value={prescription.rest_seconds ?? ""}
          onChange={(e) =>
            onChange((p) => (p.rest_seconds = e.target.value === "" ? null : Number(e.target.value)))
          }
        />
      </label>
      <input
        className="input min-w-28 grow"
        placeholder="Notes"
        value={prescription.notes ?? ""}
        onChange={(e) => onChange((p) => (p.notes = e.target.value || null))}
      />
      <MoveButtons onUp={onUp} onDown={onDown} onRemove={onRemove} />
    </div>
  );
}

export function ProgramBuilderPage() {
  const { programId } = useParams<{ programId: string }>();
  const queryClient = useQueryClient();

  const program = useQuery({
    queryKey: ["programs", programId],
    queryFn: () => api<ProgramDetail>(`/programs/${programId}`),
  });
  const exercisesQuery = useQuery({
    queryKey: ["exercises"],
    queryFn: () => api<Exercise[]>("/exercises"),
  });
  const clients = useQuery({ queryKey: ["clients"], queryFn: () => api<Client[]>("/clients") });

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [startsOn, setStartsOn] = useState("");
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<Date | null>(null);

  const syncFromServer = (data: ProgramDetail) => {
    setName(data.name);
    setDescription(data.description ?? "");
    setStartsOn(data.starts_on ?? "");
    setBlocks(structuredClone(data.blocks));
    setDirty(false);
  };

  useEffect(() => {
    if (program.data && !dirty) syncFromServer(program.data);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [program.data?.id, program.data?.updated_at]);

  const edit = (mutator: (draft: Block[]) => void) => {
    setBlocks((prev) => {
      const next = structuredClone(prev);
      mutator(next);
      return next;
    });
    setDirty(true);
    setSavedAt(null);
  };

  const save = useMutation({
    mutationFn: async () => {
      await api<Program>(`/programs/${programId}`, {
        method: "PATCH",
        body: { name, description: description || null, starts_on: startsOn || null },
      });
      return api<ProgramDetail>(`/programs/${programId}/structure`, {
        method: "PUT",
        body: { blocks },
      });
    },
    onSuccess: (data) => {
      syncFromServer(data);
      setError(null);
      setSavedAt(new Date());
      void queryClient.invalidateQueries({ queryKey: ["programs"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const assign = useMutation({
    mutationFn: (clientId: string | null) =>
      api<Program>(`/programs/${programId}`, { method: "PATCH", body: { client_id: clientId } }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["programs"] }),
    onError: (err) => setError(errorMessage(err)),
  });

  const exercises = exercisesQuery.data ?? [];
  const defaultExerciseId = exercises[0]?.id;

  if (program.isPending) return <p className="text-slate-400">Loading program…</p>;
  if (program.isError) {
    return (
      <p className="text-red-400">
        Couldn't load program. <Link className="underline" to="/">Back to programs</Link>
      </p>
    );
  }

  const addPrescription = (b: number, w: number, d: number) => {
    if (!defaultExerciseId) return;
    edit((draft) => {
      draft[b].weeks[w].days[d].prescriptions.push({
        exercise_id: defaultExerciseId,
        sets: 3,
        rep_scheme: { type: "range", min: 8, max: 12 },
        load_scheme: { type: "rpe", rpe: 8 },
        tempo: null,
        rest_seconds: 120,
        notes: null,
      });
    });
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <Link to="/" className="btn-ghost">
          ← Programs
        </Link>
        <input
          className="input min-w-60 grow text-base font-semibold"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setDirty(true);
          }}
        />
        {!program.data.is_template && (
          <select
            className="select"
            value={program.data.client_id ?? ""}
            onChange={(e) => assign.mutate(e.target.value || null)}
          >
            <option value="">Unassigned</option>
            {clients.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name}
              </option>
            ))}
          </select>
        )}
        <label className="flex items-center gap-1 text-xs text-slate-400">
          Starts
          <input
            type="date"
            className="input"
            value={startsOn}
            onChange={(e) => {
              setStartsOn(e.target.value);
              setDirty(true);
            }}
          />
        </label>
        <button type="button" className="btn" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? "Saving…" : dirty ? "Save changes" : "Saved"}
        </button>
      </div>

      <input
        className="input w-full"
        placeholder="Program description (optional)"
        value={description}
        onChange={(e) => {
          setDescription(e.target.value);
          setDirty(true);
        }}
      />

      {error && <p className="text-sm text-red-400">{error}</p>}
      {savedAt && !dirty && (
        <p className="text-xs text-emerald-500">Saved at {savedAt.toLocaleTimeString()}</p>
      )}
      {program.data.is_template && (
        <p className="text-xs text-amber-400">
          This is a template — duplicate it from the programs list to assign it to a client.
        </p>
      )}

      {blocks.map((block, b) => (
        <section key={block.id ?? `new-${b}`} className="card space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Block {b + 1}
            </span>
            <input
              className="input grow font-medium"
              value={block.name}
              onChange={(e) => edit((d) => (d[b].name = e.target.value))}
            />
            <button
              type="button"
              className="btn-ghost"
              onClick={() =>
                edit((d) => {
                  d[b].weeks.push({ name: null, days: [] });
                })
              }
            >
              + Week
            </button>
            <MoveButtons
              onUp={() => edit((d) => moveItem(d, b, b - 1))}
              onDown={() => edit((d) => moveItem(d, b, b + 1))}
              onRemove={() => edit((d) => void d.splice(b, 1))}
            />
          </div>
          <input
            className="input w-full"
            placeholder="Block notes (intent, progression rules…)"
            value={block.notes ?? ""}
            onChange={(e) => edit((d) => (d[b].notes = e.target.value || null))}
          />

          {block.weeks.map((week, w) => (
            <div key={week.id ?? `new-${w}`} className="space-y-2 rounded-md border border-slate-800 p-3">
              <div className="flex items-center gap-2">
                <input
                  className="input w-44"
                  placeholder={`Week ${w + 1}`}
                  value={week.name ?? ""}
                  onChange={(e) => edit((d) => (d[b].weeks[w].name = e.target.value || null))}
                />
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() =>
                    edit((d) => {
                      d[b].weeks[w].days.push({
                        name: null,
                        is_rest_day: false,
                        notes: null,
                        prescriptions: [],
                      });
                    })
                  }
                >
                  + Day
                </button>
                <MoveButtons
                  onUp={() => edit((d) => moveItem(d[b].weeks, w, w - 1))}
                  onDown={() => edit((d) => moveItem(d[b].weeks, w, w + 1))}
                  onRemove={() => edit((d) => void d[b].weeks.splice(w, 1))}
                />
              </div>

              {week.days.map((day, dd) => (
                <div key={day.id ?? `new-${dd}`} className="space-y-2 rounded-md bg-slate-900/70 p-2 pl-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      className="input w-44"
                      placeholder={`Day ${dd + 1}`}
                      value={day.name ?? ""}
                      onChange={(e) =>
                        edit((d) => (d[b].weeks[w].days[dd].name = e.target.value || null))
                      }
                    />
                    <label className="flex items-center gap-1.5 text-xs text-slate-400">
                      <input
                        type="checkbox"
                        checked={day.is_rest_day}
                        onChange={(e) =>
                          edit((d) => (d[b].weeks[w].days[dd].is_rest_day = e.target.checked))
                        }
                      />
                      Rest day
                    </label>
                    {!day.is_rest_day && (
                      <button type="button" className="btn-ghost" onClick={() => addPrescription(b, w, dd)}>
                        + Exercise
                      </button>
                    )}
                    <input
                      className="input min-w-28 grow"
                      placeholder="Day notes"
                      value={day.notes ?? ""}
                      onChange={(e) =>
                        edit((d) => (d[b].weeks[w].days[dd].notes = e.target.value || null))
                      }
                    />
                    <MoveButtons
                      onUp={() => edit((d) => moveItem(d[b].weeks[w].days, dd, dd - 1))}
                      onDown={() => edit((d) => moveItem(d[b].weeks[w].days, dd, dd + 1))}
                      onRemove={() => edit((d) => void d[b].weeks[w].days.splice(dd, 1))}
                    />
                  </div>
                  {!day.is_rest_day &&
                    day.prescriptions.map((rx, r) => (
                      <PrescriptionRow
                        key={rx.id ?? `new-${r}`}
                        prescription={rx}
                        exercises={exercises}
                        onChange={(mutator) =>
                          edit((d) => mutator(d[b].weeks[w].days[dd].prescriptions[r]))
                        }
                        onUp={() => edit((d) => moveItem(d[b].weeks[w].days[dd].prescriptions, r, r - 1))}
                        onDown={() => edit((d) => moveItem(d[b].weeks[w].days[dd].prescriptions, r, r + 1))}
                        onRemove={() => edit((d) => void d[b].weeks[w].days[dd].prescriptions.splice(r, 1))}
                      />
                    ))}
                </div>
              ))}
            </div>
          ))}
        </section>
      ))}

      <button
        type="button"
        className="btn-ghost"
        onClick={() =>
          edit((draft) => {
            draft.push({ name: `Block ${draft.length + 1}`, notes: null, weeks: [] });
          })
        }
      >
        + Add block
      </button>
      <p className="text-xs text-slate-600">
        * custom exercise · changes are saved only when you hit "Save changes"
      </p>
    </div>
  );
}
