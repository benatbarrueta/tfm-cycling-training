import { useCallback, useEffect, useState } from "react";
import {
  getCurrentUser,
  loginAsDemo,
  loginWithGoogle,
  logout as logoutRequest,
} from "../api/auth";
import type { ApiError } from "../api/client";
import type { AuthenticatedUser } from "../api/types";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthState {
  user: AuthenticatedUser | null;
  status: AuthStatus;
  error: string | null;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    status: "loading",
    error: null,
  });

  useEffect(() => {
    let active = true;

    getCurrentUser()
      .then((user) => {
        if (active) setState({ user, status: "authenticated", error: null });
      })
      .catch((error: ApiError) => {
        if (!active) return;
        if (error.status === 401) {
          setState({ user: null, status: "unauthenticated", error: null });
        } else {
          setState({
            user: null,
            status: "unauthenticated",
            error: error.message,
          });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const loginWithGoogleUser = useCallback(async (credential: string) => {
    const user = await loginWithGoogle(credential);
    setState({ user, status: "authenticated", error: null });
  }, []);

  const loginAsDemoUser = useCallback(async () => {
    const user = await loginAsDemo();
    setState({ user, status: "authenticated", error: null });
  }, []);

  const logout = useCallback(async () => {
    await logoutRequest();
    setState({ user: null, status: "unauthenticated", error: null });
  }, []);

  return {
    ...state,
    isAuthenticated: state.status === "authenticated",
    loginWithGoogle: loginWithGoogleUser,
    loginAsDemo: loginAsDemoUser,
    logout,
    clearError: () => setState((current) => ({ ...current, error: null })),
  };
}
