import { DarkTheme, Stack, ThemeProvider, useRouter, useSegments } from "expo-router";
import { useEffect, useState } from "react";

import { initAuth, isAuthed, onAuthChange } from "@/lib/api";
import { colors } from "@/lib/ui";

export default function RootLayout() {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    void initAuth().then(() => {
      setAuthed(isAuthed());
      setReady(true);
    });
    return onAuthChange(() => setAuthed(isAuthed()));
  }, []);

  useEffect(() => {
    if (!ready) return;
    const onLogin = segments[0] === "login";
    if (!authed && !onLogin) router.replace("/login");
    if (authed && onLogin) router.replace("/");
  }, [ready, authed, segments, router]);

  if (!ready) return null;

  return (
    <ThemeProvider value={DarkTheme}>
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="login" />
      </Stack>
    </ThemeProvider>
  );
}
