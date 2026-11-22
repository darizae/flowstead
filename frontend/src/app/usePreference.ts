import { useCallback, useEffect, useRef, useState } from "react";
import { preferences, type PreferenceState } from "../lib/cache/preferences";

/** Loads and saves the current principal's UI preferences, clearing prior private state on switch. */
export function usePreference(principalId?: string) {
  const [preference, setPreference] = useState<PreferenceState>();
  const [loading, setLoading] = useState(true);
  const previousPrincipal = useRef(principalId);
  useEffect(() => {
    let mounted = true;
    const previous = previousPrincipal.current;
    previousPrincipal.current = principalId;
    setPreference(undefined);
    setLoading(true);
    const clearPrevious =
      previous && previous !== principalId
        ? principalId
          ? preferences.remove(previous)
          : preferences.clearPrivate()
        : Promise.resolve();
    void clearPrevious
      .then(() => preferences.load(principalId))
      .then((value) => {
        if (!mounted) return;
        setPreference(value);
        setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [principalId]);
  const save = useCallback(
    (next: PreferenceState) => {
      setPreference(next);
      void preferences.save(next, principalId);
    },
    [principalId],
  );
  return { preference, loading, save };
}
