import { useCallback, useEffect, useState } from "react";
import { getCyclistProfile, saveCyclistProfile } from "../api/profile";
import type { CyclistFormValues } from "../schemas/cyclistSchema";
import type { ApiError } from "../api/client";

export function useCyclistProfile(enabled = true) {
  const [profile, setProfile] = useState<Awaited<ReturnType<typeof getCyclistProfile>> | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let active = true;
    getCyclistProfile()
      .then((value) => active && setProfile(value))
      .catch((cause: ApiError) => {
        if (!active) return;
        if (cause.status !== 404) setError(cause.message);
        setProfile(null);
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [enabled]);

  const save = useCallback(async (values: CyclistFormValues) => {
    const value = await saveCyclistProfile(values);
    setProfile(value);
    setError(null);
    return value;
  }, []);

  return { profile, loading, error, save };
}
