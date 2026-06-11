// Types shared between the trainer dashboard (web) and the client app
// (mobile). Consumed as TypeScript source; no build step. Grows with the API.

export const USER_ROLES = ["trainer", "client"] as const;
export type UserRole = (typeof USER_ROLES)[number];
