import { useRouter } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";

import { errorMessage, login, redeemInvite } from "@/lib/api";
import { kvSet } from "@/lib/db";
import { Button, Card, colors, Field, Screen, Subtle, Title } from "@/lib/ui";

export default function LoginScreen() {
  const router = useRouter();
  const [mode, setMode] = useState<"signin" | "invite">("signin");
  const [email, setEmail] = useState("");
  const [inviteToken, setInviteToken] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      if (mode === "signin") {
        await login(email.trim(), password);
        kvSet("email", email.trim().toLowerCase());
      } else {
        await redeemInvite(inviteToken.trim(), password);
      }
      router.replace("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <View style={{ marginTop: 48, gap: 16 }}>
        <Title>TrainerOS</Title>
        <Subtle>
          {mode === "signin"
            ? "Sign in with the account you created from your trainer's invite."
            : "Paste the invite token your trainer shared and choose a password."}
        </Subtle>
        <Card>
          {mode === "signin" ? (
            <Field
              label="Email"
              autoCapitalize="none"
              autoComplete="email"
              keyboardType="email-address"
              value={email}
              onChangeText={setEmail}
            />
          ) : (
            <Field
              label="Invite token"
              autoCapitalize="none"
              autoCorrect={false}
              value={inviteToken}
              onChangeText={setInviteToken}
            />
          )}
          <Field
            label={mode === "signin" ? "Password" : "Choose a password (min 8 chars)"}
            secureTextEntry
            value={password}
            onChangeText={setPassword}
          />
          {error ? <Text style={{ color: colors.danger, fontSize: 13 }}>{error}</Text> : null}
          <Button
            title={mode === "signin" ? "Sign in" : "Create account"}
            onPress={() => void submit()}
            busy={busy}
            disabled={
              password.length < 8 || (mode === "signin" ? email === "" : inviteToken === "")
            }
          />
        </Card>
        <Button
          variant="ghost"
          title={mode === "signin" ? "Have an invite token?" : "Already have an account?"}
          onPress={() => {
            setMode(mode === "signin" ? "invite" : "signin");
            setError(null);
          }}
        />
      </View>
    </Screen>
  );
}
