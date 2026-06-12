import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Alert, Text } from "react-native";

import { api, API_URL, logout } from "@/lib/api";
import { clearAllLocal, kvGet, kvSet, pendingCount } from "@/lib/db";
import { isSyncing, onSyncStateChange, syncNow } from "@/lib/sync";
import { Button, Card, colors, Screen, Subtle, Title } from "@/lib/ui";

export default function AccountScreen() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(() => kvGet("email"));
  const [pending, setPending] = useState<number>(() => pendingCount());
  const [syncing, setSyncing] = useState(isSyncing());

  useEffect(() => {
    // Cache identity for offline display.
    void (async () => {
      try {
        const me = await api<{ email: string }>("/auth/me");
        kvSet("email", me.email);
        setEmail(me.email);
      } catch {
        // offline
      }
    })();
    return onSyncStateChange(() => {
      setSyncing(isSyncing());
      setPending(pendingCount());
    });
  }, []);

  useFocusEffect(
    useCallback(() => {
      setPending(pendingCount());
    }, []),
  );

  const doSync = async () => {
    try {
      const result = await syncNow();
      setPending(pendingCount());
      if (result.rejected > 0) {
        Alert.alert("Sync finished", `${result.pushed} synced, ${result.rejected} rejected.`);
      }
    } catch {
      Alert.alert("Offline", "Couldn't reach the server — will retry automatically.");
    }
  };

  const doLogout = () => {
    Alert.alert("Log out?", "Unsynced workouts on this device will be deleted.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Log out",
        style: "destructive",
        onPress: () => {
          clearAllLocal();
          void logout().then(() => router.replace("/login"));
        },
      },
    ]);
  };

  return (
    <Screen>
      <Title>Account</Title>
      <Card>
        <Text style={{ color: colors.text, fontWeight: "600" }}>{email ?? "Signed in"}</Text>
        <Subtle>Server: {API_URL}</Subtle>
      </Card>
      <Card>
        <Text style={{ color: colors.text, fontWeight: "600" }}>
          {pending === 0
            ? "All workouts synced ✓"
            : `${pending} workout${pending === 1 ? "" : "s"} waiting to sync`}
        </Text>
        <Subtle>Logs sync automatically whenever the device is online.</Subtle>
        <Button title="Sync now" onPress={() => void doSync()} busy={syncing} />
      </Card>
      <Button variant="danger" title="Log out" onPress={doLogout} />
    </Screen>
  );
}
