import { useCallback, useEffect, useRef, useState } from 'react';
import type { ApiClient } from '../../lib/api/client';
import type { PlantSummary } from '../../lib/api/types';
import { useRequestState } from '../../shared/hooks/useRequestState';

/** Loads the Plant list for the current public/principal scope, gating results on scope identity. */
export function usePlants(client: ApiClient, scopeKey = 'public') {
  const [plants, setPlants] = useState<PlantSummary[]>([]);
  const scopeRef = useRef(scopeKey);
  const scopeReady = scopeRef.current === scopeKey;
  const { loading, error, run, reset } = useRequestState(true, 'Unable to load Plants.');

  const load = useCallback(async () => {
    await run(async () => {
      const result = await client.listPlants();
      setPlants(result.plants);
    });
  }, [client, run]);

  useEffect(() => {
    scopeRef.current = scopeKey;
    reset(true);
    setPlants([]);
    void load();
  }, [load, scopeKey, reset]);

  return { plants: scopeReady ? plants : [], error: scopeReady ? error : undefined, loading: scopeReady ? loading : true, retry: load };
}