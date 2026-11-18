import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, type LatestResponse, type PlantSummary } from '../lib/api/types';
import { preferences, type PreferenceState } from '../lib/cache/preferences';
import type { ApiClient } from '../lib/api/client';

export function usePlants(client: ApiClient, scopeKey = 'public') {
  const [plants, setPlants] = useState<PlantSummary[]>([]);
  const [error, setError] = useState<ApiError>();
  const [loading, setLoading] = useState(true);
  const scopeRef = useRef(scopeKey);
  const scopeReady = scopeRef.current === scopeKey;
  const requestGeneration = useRef(0);
  const load = useCallback(async () => {
    const request = ++requestGeneration.current;
    setLoading(true); setError(undefined);
    try {
      const result = await client.listPlants();
      if (request !== requestGeneration.current) return;
      setPlants(result.plants);
    } catch (cause) {
      if (request !== requestGeneration.current) return;
      setPlants([]);
      setError(cause instanceof ApiError ? cause : new ApiError('http', 'Unable to load Plants.'));
    } finally {
      if (request === requestGeneration.current) setLoading(false);
    }
  }, [client, scopeKey]);
  useEffect(() => {
    scopeRef.current = scopeKey;
    requestGeneration.current += 1;
    setPlants([]);
    setError(undefined);
    setLoading(true);
    void load();
  }, [load, scopeKey]);
  return { plants: scopeReady ? plants : [], error: scopeReady ? error : undefined, loading: scopeReady ? loading : true, retry: load };
}

export function usePlantLatest(client: ApiClient, plantId: string | undefined, scopeKey = 'public') {
  const [latest, setLatest] = useState<LatestResponse>();
  const [error, setError] = useState<ApiError>();
  const [loading, setLoading] = useState(Boolean(plantId));
  const scopeRef = useRef(scopeKey);
  const scopeReady = scopeRef.current === scopeKey;
  const plantRef = useRef(plantId);
  const plantReady = plantRef.current === plantId;
  const requestGeneration = useRef(0);
  const load = useCallback(async () => {
    const request = ++requestGeneration.current;
    if (!plantId) {
      setLatest(undefined);
      setError(undefined);
      setLoading(false);
      return;
    }
    setLoading(true); setError(undefined);
    try {
      const result = await client.latestPlant(plantId);
      if (request !== requestGeneration.current) return;
      setLatest(result);
    } catch (cause) {
      if (request !== requestGeneration.current) return;
      setLatest(undefined);
      setError(cause instanceof ApiError ? cause : new ApiError('http', 'Unable to load Plant details.'));
    } finally {
      if (request === requestGeneration.current) setLoading(false);
    }
  }, [client, plantId, scopeKey]);
  useEffect(() => {
    scopeRef.current = scopeKey;
    plantRef.current = plantId;
    requestGeneration.current += 1;
    setLatest(undefined);
    setError(undefined);
    setLoading(Boolean(plantId));
    void load();
  }, [load, plantId, scopeKey]);
  return { latest: scopeReady && plantReady ? latest : undefined, error: scopeReady && plantReady ? error : undefined, loading: scopeReady && plantReady ? loading : true, retry: load };
}

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
    const clearPrevious = previous && previous !== principalId
      ? (principalId ? preferences.remove(previous) : preferences.clearPrivate())
      : Promise.resolve();
    void clearPrevious
      .then(() => preferences.load(principalId))
      .then((value) => {
        if (!mounted) return;
        setPreference(value);
        setLoading(false);
      });
    return () => { mounted = false; };
  }, [principalId]);
  const save = useCallback((next: PreferenceState) => {
    setPreference(next);
    void preferences.save(next, principalId);
  }, [principalId]);
  return { preference, loading, save };
}
