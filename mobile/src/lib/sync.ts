import NetInfo from "@react-native-community/netinfo";

import { api, isAuthed } from "./api";
import { markLogRejected, markLogSynced, pendingLogs } from "./db";
import type { SyncResponse } from "./types";

let syncing = false;
const listeners = new Set<() => void>();

export function onSyncStateChange(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function emit(): void {
  for (const listener of listeners) listener();
}

export function isSyncing(): boolean {
  return syncing;
}

export async function syncNow(): Promise<{ pushed: number; rejected: number }> {
  if (syncing || !isAuthed()) return { pushed: 0, rejected: 0 };
  const queue = pendingLogs();
  if (queue.length === 0) return { pushed: 0, rejected: 0 };

  syncing = true;
  emit();
  try {
    const response = await api<SyncResponse>("/me/sync", {
      method: "POST",
      body: { workout_logs: queue },
    });
    let pushed = 0;
    let rejected = 0;
    for (const result of response.results) {
      if (result.status === "rejected") {
        rejected += 1;
        markLogRejected(result.id, result.detail ?? "rejected");
      } else {
        pushed += 1;
        markLogSynced(result.id);
      }
    }
    return { pushed, rejected };
  } finally {
    syncing = false;
    emit();
  }
}

/** Pushes the queue whenever connectivity returns. Returns an unsubscribe. */
export function startAutoSync(): () => void {
  return NetInfo.addEventListener((state) => {
    if (state.isConnected) {
      void syncNow().catch(() => {
        // offline or server unreachable — queue stays put for the next try
      });
    }
  });
}
