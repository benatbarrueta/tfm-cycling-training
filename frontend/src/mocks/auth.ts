import type { AuthSession } from "../hooks/useAuth";

export type AuthScenario =
  | "logged-out"
  | "google-idle"
  | "google-loading"
  | "google-unavailable"
  | "google-error"
  | "demo-authenticated"
  | "first-login"
  | "returning-user";

export const demoAuthSession: AuthSession = {
  status: "authenticated",
  mode: "demo",
  user: {
    id: "demo-user",
    name: "Ciclista Demo",
    email: "demo@veloform.local",
    avatarUrl: null,
  },
};
