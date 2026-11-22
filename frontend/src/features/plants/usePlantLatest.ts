import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiClient } from "../../lib/api/client";
import type { LatestResponse } from "../../lib/api/types";
import { useRequestState } from "../../shared/hooks/useRequestState";

/** Loads a single Plant's latest measurements, gated on scope and Plant identity. */
export function usePlantLatest(
  client: ApiClient,
  plantId: string | undefined,
  scopeKey = "public",
) {
  const [latest, setLatest] = useState<LatestResponse>();
  const scopeRef = useRef(scopeKey);
  const scopeReady = scopeRef.current === scopeKey;
  const plantRef = useRef(plantId);
  const plantReady = plantRef.current === plantId;
  const { loading, error, run, reset } = useRequestState(
    Boolean(plantId),
    "Unable to load Plant details.",
  );

  const load = useCallback(async () => {
    if (!plantId) {
      reset(false);
      setLatest(undefined);
      return;
    }
    await run(async () => {
      const result = await client.latestPlant(plantId);
      setLatest(result);
    });
  }, [client, plantId, reset, run]);

  useEffect(() => {
    scopeRef.current = scopeKey;
    plantRef.current = plantId;
    reset(Boolean(plantId));
    setLatest(undefined);
    void load();
  }, [load, plantId, scopeKey, reset]);

  return {
    latest: scopeReady && plantReady ? latest : undefined,
    error: scopeReady && plantReady ? error : undefined,
    loading: scopeReady && plantReady ? loading : true,
    retry: load,
  };
}
