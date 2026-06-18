import { Tabs } from "expo-router";
import { useEffect } from "react";
import { Text } from "react-native";

import { startAutoSync, syncNow } from "@/lib/sync";
import { colors } from "@/lib/ui";

function icon(glyph: string) {
  return ({ focused }: { focused: boolean }) => (
    <Text style={{ fontSize: 18, opacity: focused ? 1 : 0.5 }}>{glyph}</Text>
  );
}

export default function TabsLayout() {
  useEffect(() => {
    // Push anything queued while offline, then keep watching connectivity.
    void syncNow().catch(() => {});
    return startAutoSync();
  }, []);

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg },
        headerTitleStyle: { color: colors.text },
        headerShadowVisible: false,
        tabBarStyle: { backgroundColor: colors.bg, borderTopColor: colors.border },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.dim,
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Today", tabBarIcon: icon("🏋️") }} />
      <Tabs.Screen name="program" options={{ title: "Program", tabBarIcon: icon("📋") }} />
      <Tabs.Screen name="check-in" options={{ title: "Check-in", tabBarIcon: icon("📸") }} />
      <Tabs.Screen name="account" options={{ title: "Account", tabBarIcon: icon("👤") }} />
    </Tabs>
  );
}
