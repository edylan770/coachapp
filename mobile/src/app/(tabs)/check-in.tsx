import Slider from "@react-native-community/slider";
import NetInfo from "@react-native-community/netinfo";
import * as Crypto from "expo-crypto";
import * as ImagePicker from "expo-image-picker";
import { useEffect, useState } from "react";
import { Alert, Image, Pressable, Text, View } from "react-native";

import { api, errorMessage } from "@/lib/api";
import type { CheckInOut } from "@/lib/types";
import { Button, Card, colors, Field, Screen, Subtle, Title } from "@/lib/ui";

const MEASUREMENT_FIELDS = ["waist", "chest", "hips", "arm", "thigh"] as const;

function AdherenceSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <View style={{ gap: 2 }}>
      <Text style={{ color: colors.dim, fontSize: 12 }}>
        {label}: <Text style={{ color: colors.text, fontWeight: "700" }}>{value}/5</Text>
      </Text>
      <Slider
        minimumValue={1}
        maximumValue={5}
        step={1}
        value={value}
        onValueChange={onChange}
        minimumTrackTintColor={colors.accent}
        maximumTrackTintColor={colors.border}
        thumbTintColor={colors.accent}
      />
    </View>
  );
}

export default function CheckInScreen() {
  const [weight, setWeight] = useState("");
  const [unit, setUnit] = useState<"kg" | "lb">("kg");
  const [measurements, setMeasurements] = useState<Record<string, string>>({});
  const [training, setTraining] = useState(3);
  const [nutrition, setNutrition] = useState(3);
  const [sleep, setSleep] = useState(3);
  const [notes, setNotes] = useState("");
  const [photos, setPhotos] = useState<ImagePicker.ImagePickerAsset[]>([]);
  const [busy, setBusy] = useState(false);
  const [lastSubmitted, setLastSubmitted] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const recent = await api<CheckInOut[]>("/me/check-ins?limit=1");
        setLastSubmitted(recent[0]?.check_in_date ?? null);
      } catch {
        // offline — fine
      }
    })();
  }, []);

  const pickPhotos = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      allowsMultipleSelection: true,
      selectionLimit: 4,
      quality: 0.7,
    });
    if (!result.canceled) {
      setPhotos((prev) => [...prev, ...result.assets].slice(0, 4));
    }
  };

  const submit = async () => {
    const net = await NetInfo.fetch();
    if (!net.isConnected) {
      Alert.alert("You're offline", "Check-ins need a connection (photos upload directly).");
      return;
    }
    setBusy(true);
    try {
      const keys: string[] = [];
      for (const [index, asset] of photos.entries()) {
        const form = new FormData();
        form.append("file", {
          uri: asset.uri,
          name: asset.fileName ?? `photo-${index}.jpg`,
          type: asset.mimeType ?? "image/jpeg",
        } as unknown as Blob);
        const uploaded = await api<{ key: string }>("/me/check-ins/photos", {
          method: "POST",
          formData: form,
        });
        keys.push(uploaded.key);
      }

      const m: Record<string, number> = {};
      for (const field of MEASUREMENT_FIELDS) {
        const raw = (measurements[field] ?? "").trim().replace(",", ".");
        if (raw !== "" && Number.isFinite(Number(raw))) m[field] = Number(raw);
      }
      const weightNum = Number(weight.trim().replace(",", "."));

      await api("/me/check-ins", {
        method: "POST",
        body: {
          id: Crypto.randomUUID(),
          check_in_date: new Date().toISOString().slice(0, 10),
          weight: weight.trim() !== "" && Number.isFinite(weightNum) ? weightNum : null,
          weight_unit: unit,
          measurements: Object.keys(m).length > 0 ? m : null,
          photos: keys,
          adherence: { training, nutrition, sleep },
          notes: notes.trim() === "" ? null : notes.trim(),
        },
      });

      setWeight("");
      setMeasurements({});
      setNotes("");
      setPhotos([]);
      setLastSubmitted(new Date().toISOString().slice(0, 10));
      Alert.alert("Check-in sent", "Your trainer will get back to you.");
    } catch (error) {
      Alert.alert("Couldn't submit", errorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <Title>Weekly check-in</Title>
      <Subtle>
        {lastSubmitted ? `Last submitted ${lastSubmitted}.` : "No check-ins from this device yet."}
      </Subtle>

      <Card>
        <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 8 }}>
          <View style={{ flex: 1 }}>
            <Field
              label={`Body weight (${unit})`}
              keyboardType="decimal-pad"
              value={weight}
              onChangeText={setWeight}
            />
          </View>
          <Button
            variant="ghost"
            title={unit.toUpperCase()}
            onPress={() => setUnit(unit === "kg" ? "lb" : "kg")}
          />
        </View>
      </Card>

      <Card>
        <Text style={{ color: colors.text, fontWeight: "600" }}>Measurements (optional)</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {MEASUREMENT_FIELDS.map((field) => (
            <View key={field} style={{ width: "30%", flexGrow: 1 }}>
              <Field
                label={field}
                keyboardType="decimal-pad"
                value={measurements[field] ?? ""}
                onChangeText={(v) => setMeasurements((prev) => ({ ...prev, [field]: v }))}
              />
            </View>
          ))}
        </View>
      </Card>

      <Card>
        <Text style={{ color: colors.text, fontWeight: "600" }}>Adherence this week</Text>
        <AdherenceSlider label="Training" value={training} onChange={setTraining} />
        <AdherenceSlider label="Nutrition" value={nutrition} onChange={setNutrition} />
        <AdherenceSlider label="Sleep" value={sleep} onChange={setSleep} />
      </Card>

      <Card>
        <Text style={{ color: colors.text, fontWeight: "600" }}>Photos ({photos.length}/4)</Text>
        <View style={{ flexDirection: "row", gap: 8, flexWrap: "wrap" }}>
          {photos.map((asset, index) => (
            <Pressable
              key={`${asset.assetId ?? asset.uri}-${index}`}
              onLongPress={() => setPhotos((prev) => prev.filter((_, i) => i !== index))}
            >
              <Image
                source={{ uri: asset.uri }}
                style={{ width: 72, height: 72, borderRadius: 8 }}
              />
            </Pressable>
          ))}
        </View>
        <Subtle>Long-press a photo to remove it.</Subtle>
        <Button variant="ghost" title="Add photos" onPress={() => void pickPhotos()} />
      </Card>

      <Card>
        <Field
          label="How did the week go?"
          multiline
          numberOfLines={4}
          style={{ minHeight: 90, textAlignVertical: "top" }}
          value={notes}
          onChangeText={setNotes}
        />
      </Card>

      <Button title="Submit check-in" onPress={() => void submit()} busy={busy} />
    </Screen>
  );
}
