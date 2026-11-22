import { useCallback, useEffect, useRef, useState } from 'react';
import type { ApiClient } from '../../lib/api/client';
import { ApiError, type ForecastResponse } from '../../lib/api/types';
import { preferences } from '../../lib/cache/preferences';
import { useRequestState } from '../../shared/hooks/useRequestState';

/** Loads a Plant's forecast, gated on scope and Plant identity, persisting an authorized snapshot. */
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
      if (result.status !== 'available' && result.status !== 'unavailable') {
        throw new ApiError('invalid_response', 'Flowstead returned an unreadable forecast response.');
      }
      setForecast(result);
      // Persist a sanitized snapshot only after this fresh authorized response.
      if (scopeKey !== 'mock:public') {
        await preferences.saveForecast(plantId, result, scopeKey === 'public' ? undefined : scopeKey.replace(/^principal:/, ''));
      }
    });
  }, [client, plantId, run, scopeKey]);

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