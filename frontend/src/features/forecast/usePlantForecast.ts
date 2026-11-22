import { useCallback, useEffect, useRef, useState } from 'react';
import type { ApiClient } from '../../lib/api/client';
import type { ForecastResponse } from '../../lib/api/types';
import { useRequestState } from '../../shared/hooks/useRequestState';

/** Loads a Plant's forecast, gated on scope and Plant identity. */
export function usePlantForecast(client: ApiClient, plantId: string | undefined, scopeKey = 'public') {
  const [forecast, setForecast] = useState<ForecastResponse>();
  const scopeRef = useRef(scopeKey);
  const scopeReady = scopeRef.current === scopeKey;
  const plantRef = useRef(plantId);
  const plantReady = plantRef.current === plantId;
  const { loading, error, run, reset } = useRequestState(Boolean(plantId), 'Unable to load Plant forecast.');

  const load = useCallback(async () => {
    if (!plantId) {
      reset(false);
      setForecast(undefined);
      return;
    }
    await run(async () => {
      const result = await client.forecastPlant(plantId);
      setForecast(result);
    });
  }, [client, plantId, run]);

  useEffect(() => {
    scopeRef.current = scopeKey;
    plantRef.current = plantId;
    reset(Boolean(plantId));
    setForecast(undefined);
    void load();
  }, [load, plantId, reset, scopeKey]);

  return {
    forecast: scopeReady && plantReady ? forecast : undefined,
    error: scopeReady && plantReady ? error : undefined,
    loading: scopeReady && plantReady ? loading : true,
    retry: load,
  };
}