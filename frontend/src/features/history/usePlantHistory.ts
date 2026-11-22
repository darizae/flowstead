import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiClient } from "../../lib/api/client";
import type { HistoryResponse } from "../../lib/api/types";
import { useRequestState } from "../../shared/hooks/useRequestState";
import { historyWindow, type HistoryRange } from "./transforms";

/** Loads a Plant's history window, gated on scope, Plant, anchor timestamp, and range identity. */
export function usePlantHistory(
  client: ApiClient,
  plantId: string | undefined,
  range: HistoryRange,
  scopeKey = "public",
  latestTimestampUtc?: string,
) {
  const [history, setHistory] = useState<HistoryResponse>();
  const scopeRef = useRef(scopeKey);
  const scopeReady = scopeRef.current === scopeKey;
  const plantRef = useRef(plantId);
  const plantReady = plantRef.current === plantId;
  const anchorRef = useRef(latestTimestampUtc);
  const anchorReady = anchorRef.current === latestTimestampUtc;
  const rangeRef = useRef(range);
  const rangeReady = rangeRef.current === range;
  const { loading, error, run, reset } = useRequestState(
    Boolean(plantId && latestTimestampUtc),
    "Unable to load Plant history.",
  );

  const load = useCallback(async () => {
    if (!plantId || !latestTimestampUtc) {
      reset(false);
      setHistory(undefined);
      return;
    }
    await run(async () => {
      const { from, to } = historyWindow(range, latestTimestampUtc);
      const result = await client.historyPlant(plantId, from, to);
      setHistory(result);
    });
  }, [client, latestTimestampUtc, plantId, range, reset, run]);

  useEffect(() => {
    scopeRef.current = scopeKey;
    plantRef.current = plantId;
    anchorRef.current = latestTimestampUtc;
    rangeRef.current = range;
    reset(Boolean(plantId && latestTimestampUtc));
    setHistory(undefined);
    void load();
  }, [load, latestTimestampUtc, plantId, range, reset, scopeKey]);

  return {
    history:
      scopeReady && plantReady && anchorReady && rangeReady
        ? history
        : undefined,
    error:
      scopeReady && plantReady && anchorReady && rangeReady ? error : undefined,
    loading:
      scopeReady && plantReady && anchorReady && rangeReady ? loading : true,
    retry: load,
  };
}
