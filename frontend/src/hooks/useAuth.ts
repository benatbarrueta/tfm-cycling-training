import { useCallback, useEffect, useState } from "react";
import { storageKeys } from "../config/storage";
import { demoAuthSession } from "../mocks/auth";

export type AuthStatus = "authenticated";
export type AuthMode = "demo";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  avatarUrl: string | null;
}

export interface AuthSession {
  status: AuthStatus;
  mode: AuthMode;
  user: AuthUser;
}

function parseDemoSession(value: unknown): AuthSession | null {
  if (
    typeof value === "object" &&
    value !== null &&
    "status" in value &&
    "mode" in value &&
    "user" in value &&
    value.status === "authenticated" &&
    value.mode === "demo" &&
    typeof value.user === "object" &&
    value.user !== null &&
    "id" in value.user &&
    "name" in value.user &&
    "email" in value.user &&
    typeof value.user.id === "string" &&
    typeof value.user.name === "string" &&
    typeof value.user.email === "string"
  ) {
    return {
      status: "authenticated",
      mode: "demo",
      user: {
        id: value.user.id,
        name: value.user.name,
        email: value.user.email,
        avatarUrl: null,
      },
    };
  }

  return null;
}

function readSession(key: string): AuthSession | null {
  const saved = localStorage.getItem(key);
  if (saved === null) return null;

  try {
    return parseDemoSession(JSON.parse(saved));
  } catch {
    localStorage.removeItem(key);
    return null;
  }
}

function loadSession(): AuthSession | null {
  return readSession(storageKeys.demoSession) ?? readSession(storageKeys.session);
}

export function useAuth() {
  const [session, setSession] = useState<AuthSession | null>(loadSession);

  useEffect(() => {
    if (session === null) {
      localStorage.removeItem(storageKeys.demoSession);
      localStorage.removeItem(storageKeys.session);
    } else {
      localStorage.setItem(storageKeys.demoSession, JSON.stringify(session));
      localStorage.removeItem(storageKeys.session);
    }
  }, [session]);

  const signInDemo = useCallback(() => {
    setSession(demoAuthSession);
  }, []);

  const signOut = useCallback(() => {
    setSession(null);
  }, []);

  return {
    session,
    user: session?.user ?? null,
    isAuthenticated: session !== null,
    isDemo: session?.mode === "demo",
    signInDemo,
    signOut,
  };
}
