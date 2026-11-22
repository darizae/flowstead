import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, type ForecastJobStatus, type ForecastResponse, type HistoryResponse, type LatestResponse, type PlantSummary } from '../lib/api/types';
import { preferences, type PreferenceState } from '../lib/cache/preferences';
import type { ApiClient } from '../lib/api/client';
import { historyWindow, type HistoryRange } from '../features/history/transforms';
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

export function usePlantHistory(client: ApiClient, plantId: string | undefined, range: 24 | 72 | 168, scopeKey = 'public', latestTimestampUtc?: string) {
  const [history, setHistory] = useState<HistoryResponse>();
  const [error, setError] = useState<ApiError>();
  const [loading, setLoading] = useState(Boolean(plantId && latestTimestampUtc));
  const scopeRef = useRef(scopeKey);
  const scopeReady = scopeRef.current === scopeKey;
  const plantRef = useRef(plantId);
  const plantReady = plantRef.current === plantId;
  const anchorRef = useRef(latestTimestampUtc);
  const anchorReady = anchorRef.current === latestTimestampUtc;
  const rangeRef = useRef(range);
  const rangeReady = rangeRef.current === range;
  const requestGeneration = useRef(0);
  const load = useCallback(async () => {
    const request = ++requestGeneration.current;
    if (!plantId || !latestTimestampUtc) {
      setHistory(undefined); setError(undefined); setLoading(false); return;
    }
    setLoading(true); setError(undefined);
    try {
      const { from, to } = historyWindow(range, latestTimestampUtc);
      const result = await client.historyPlant(plantId, from, to);
      if (request !== requestGeneration.current) return;
      if (!Array.isArray(result.readings)) throw new ApiError('invalid_response', 'Flowstead returned an unreadable history response.');
      setHistory(result);
    } catch (cause) {
      if (request !== requestGeneration.current) return;
      setHistory(undefined);
      setError(cause instanceof ApiError ? cause : new ApiError('http', 'Unable to load Plant history.'));
    } finally {
      if (request === requestGeneration.current) setLoading(false);
    }
  }, [client, plantId, range, scopeKey, latestTimestampUtc]);
  useEffect(() => {
    scopeRef.current = scopeKey;
    plantRef.current = plantId;
    anchorRef.current = latestTimestampUtc;
    rangeRef.current = range;
    requestGeneration.current += 1;
    setHistory(undefined); setError(undefined); setLoading(Boolean(plantId && latestTimestampUtc));
    if (plantId && latestTimestampUtc) void load();
  }, [load, plantId, range, scopeKey, latestTimestampUtc]);
  return {
    history: scopeReady && plantReady && anchorReady && rangeReady ? history : undefined,
    error: scopeReady && plantReady && anchorReady && rangeReady ? error : undefined,
    loading: scopeReady && plantReady && anchorReady && rangeReady ? loading : true,
    retry: load,
  };
}

export function usePlantForecast(client: ApiClient, plantId: string | undefined, scopeKey = 'public') {
  const [forecast, setForecast] = useState<ForecastResponse>();
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
      setForecast(undefined); setError(undefined); setLoading(false); return;
    }
    setLoading(true); setError(undefined);
    try {
      const result = await client.forecastPlant(plantId);
      if (request !== requestGeneration.current) return;
      if (result.status !== 'available' && result.status !== 'unavailable') {
        throw new ApiError('invalid_response', 'Flowstead returned an unreadable forecast response.');
      }
      setForecast(result);
      // Persist a sanitized snapshot only after this fresh authorized response.
      if (scopeKey !== 'mock:public') {
        await preferences.saveForecast(plantId, result, scopeKey === 'public' ? undefined : scopeKey.replace(/^principal:/, ''));
      }
    } catch (cause) {
      if (request !== requestGeneration.current) return;
      setForecast(undefined);
      setError(cause instanceof ApiError ? cause : new ApiError('http', 'Unable to load Plant forecast.'));
    } finally {
      if (request === requestGeneration.current) setLoading(false);
    }
  }, [client, plantId, scopeKey]);
  useEffect(() => {
    scopeRef.current = scopeKey;
    plantRef.current = plantId;
    requestGeneration.current += 1;
    setForecast(undefined); setError(undefined); setLoading(Boolean(plantId));
    if (plantId) void load();
  }, [load, plantId, scopeKey]);
  return {
    forecast: scopeReady && plantReady ? forecast : undefined,
    error: scopeReady && plantReady ? error : undefined,
    loading: scopeReady && plantReady ? loading : true,
    retry: load,
  };
}

export function useForecastRequest(
  client: ApiClient,
  plantId: string | undefined,
  scopeKey: string,
  onCompleted: () => Promise<unknown>,
) {
  const [status, setStatus] = useState<ForecastJobStatus>();
  const [error, setError] = useState<ApiError>();
  const requestGeneration = useRef(0);
  useEffect(() => {
    requestGeneration.current += 1;
    setStatus(undefined);
    setError(undefined);
    return () => { requestGeneration.current += 1; };
  }, [plantId, scopeKey]);
  const refresh = useCallback(async () => {
    if (!plantId || scopeKey === 'public') return;
    const request = ++requestGeneration.current;
    setError(undefined);
    try {
      let job = await client.requestForecast(plantId);
      if (request !== requestGeneration.current) return;
      setStatus(job.status);
      for (const delay of [250, 500, 1_000, 2_000, 2_000, 2_000, 2_000]) {
        if (job.status === 'completed' || job.status === 'failed') break;
        const { promise, resolve } = Promise.withResolvers<void>();
        window.setTimeout(resolve, delay);
        await promise;
        if (request !== requestGeneration.current) return;
        job = await client.forecastRequest(job.correlation_id);
        if (request !== requestGeneration.current) return;
        setStatus(job.status);
      }
      if (job.status === 'completed') {
        await onCompleted();
      } else if (job.status === 'failed') {
        throw new ApiError('http', 'Forecast refresh failed.');
      } else {
        throw new ApiError('network', 'Forecast refresh timed out. Try again.');
      }
    } catch (cause) {
      if (request !== requestGeneration.current) return;
      setError(cause instanceof ApiError ? cause : new ApiError('http', 'Unable to refresh forecast.'));
      setStatus('failed');
    }
  }, [client, onCompleted, plantId, scopeKey]);
  return { status, error, refresh };
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
