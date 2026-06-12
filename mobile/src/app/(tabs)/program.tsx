import { useFocusEffect } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { Text, View } from "react-native";

import { loggedDayIds } from "@/lib/db";
import { getCachedProgram, prescriptionSummary } from "@/lib/program";
import type { CachedProgram } from "@/lib/types";
import { Card, colors, Screen, Subtle, Title } from "@/lib/ui";

export default function ProgramScreen() {
  const [cache, setCache] = useState<CachedProgram | null>(() => getCachedProgram());
  const [logged, setLogged] = useState<Set<string>>(() => new Set(loggedDayIds()));

  useFocusEffect(
    useCallback(() => {
      setCache(getCachedProgram());
      setLogged(new Set(loggedDayIds()));
    }, []),
  );

  const exerciseName = useMemo(() => {
    const map = new Map((cache?.exercises ?? []).map((e) => [e.id, e.name]));
    return (id: string) => map.get(id) ?? "Exercise";
  }, [cache]);

  if (!cache) {
    return (
      <Screen>
        <Title>Program</Title>
        <Subtle>No program assigned yet — check the Today tab to fetch one.</Subtle>
      </Screen>
    );
  }

  return (
    <Screen>
      <Title>{cache.program.name}</Title>
      {cache.program.description ? <Subtle>{cache.program.description}</Subtle> : null}

      {cache.program.blocks.map((block, blockIndex) => (
        <Card key={block.id}>
          <Text style={{ color: colors.text, fontSize: 16, fontWeight: "700" }}>
            {block.name}
          </Text>
          {block.notes ? <Subtle>{block.notes}</Subtle> : null}

          {block.weeks.map((week, weekIndex) => (
            <View key={week.id} style={{ gap: 6, marginTop: 4 }}>
              <Text style={{ color: colors.dim, fontWeight: "600", fontSize: 13 }}>
                {week.name ?? `Week ${weekIndex + 1}`}
              </Text>
              {week.days.map((day, dayIndex) => (
                <View
                  key={day.id}
                  style={{
                    borderColor: colors.border,
                    borderWidth: 1,
                    borderRadius: 8,
                    padding: 8,
                    gap: 2,
                  }}
                >
                  <Text style={{ color: colors.text, fontWeight: "600" }}>
                    {logged.has(day.id) ? "✅ " : ""}
                    {day.name ?? `Day ${dayIndex + 1}`}
                    {day.is_rest_day ? " — rest" : ""}
                  </Text>
                  {day.prescriptions.map((rx) => (
                    <Subtle key={rx.id}>
                      {exerciseName(rx.exercise_id)} —{" "}
                      {prescriptionSummary(rx.sets, rx.rep_scheme, rx.load_scheme)}
                    </Subtle>
                  ))}
                </View>
              ))}
            </View>
          ))}
        </Card>
      ))}
      <Subtle>Read-only — your trainer manages the plan.</Subtle>
    </Screen>
  );
}
