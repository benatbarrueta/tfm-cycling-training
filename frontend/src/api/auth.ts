import { apiRequest } from "./client";
import type { AuthenticatedUser } from "./types";

export function getCurrentUser() {
  return apiRequest<AuthenticatedUser>("/api/auth/me");
}

export function loginWithGoogle(credential: string) {
  return apiRequest<AuthenticatedUser>("/api/auth/google", {
    method: "POST",
    body: JSON.stringify({ credential }),
  });
}

export function loginAsDemo() {
  return apiRequest<AuthenticatedUser>("/api/auth/demo", {
    method: "POST",
  });
}

export function logout() {
  return apiRequest<void>("/api/auth/logout", { method: "POST" });
}
