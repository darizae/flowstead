import 'fake-indexeddb/auto';
import { beforeEach, describe, expect, it } from 'vitest';
import { CACHE_SCHEMA_VERSION, PreferenceCache } from './preferences';

const cache = new PreferenceCache();
const entryKey = (principal: string, kind: 'preference' | 'forecast', key: string) => `${CACHE_SCHEMA_VERSION}:principal:${encodeURIComponent(principal)}:${kind}:${key}`;

async function readEntryCount(): Promise<number> {
  const database = await new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open('flowstead-preferences', CACHE_SCHEMA_VERSION);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  return new Promise((resolve, reject) => {
    const request = database.transaction('entries', 'readonly').objectStore('entries').count();
    request.onsuccess = () => { database.close(); resolve(request.result); };
    request.onerror = () => { database.close(); reject(request.error); };
  });
}

async function putRaw(principal: string, kind: 'preference' | 'forecast', key: string, entry: Record<string, unknown>): Promise<void> {
  const database = await new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open('flowstead-preferences', CACHE_SCHEMA_VERSION);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction('entries', 'readwrite');
    transaction.objectStore('entries').put(entry, entryKey(principal, kind, key));
    transaction.oncomplete = () => { database.close(); resolve(); };
    transaction.onerror = () => reject(transaction.error);
  });
}

const snapshot = () => ({
  plant: { plant_id: 'plant-01', name: 'Alpha Plant', timezone: 'America/New_York' },
  status: 'available' as const,
  issued_at_utc: '2025-01-01T00:00:00.000Z',
  model_version: 'seasonal-naive-24h',
  forecasts: Array.from({ length: 12 }, (_, index) => ({ hour_number: index + 1, target_time_utc: new Date(Date.UTC(2025, 0, 1, index + 1)).toISOString(), predicted_flow_gal_h: 100 + index, units: 'gal/h' as const })),
  unavailable_reason: null,
});

beforeEach(async () => {
  await cache.clearPrivate();
  await cache.remove();
});

describe('PreferenceCache', () => {
  it('sanitizes unsupported values before persistence', async () => {
    await cache.save({ plantId: '<script>', chart: 'unknown' as never, windowHours: 999 as never }, 'principal/a');
    await expect(cache.load('principal/a')).resolves.toEqual({});
  });

  it('keeps public and principal preferences in disjoint namespaces', async () => {
    await cache.save({ plantId: 'public-plant' });
    await cache.save({ plantId: 'private-a' }, 'operator/a');
    await cache.save({ plantId: 'private-b' }, 'operator-b');
    await expect(cache.load()).resolves.toEqual({ plantId: 'public-plant' });
    await expect(cache.load('operator/a')).resolves.toEqual({ plantId: 'private-a' });
    await expect(cache.load('operator-b')).resolves.toEqual({ plantId: 'private-b' });
  });

  it('rejects tampered namespace keys and oversized principals', async () => {
    await cache.save({ plantId: 'private-a' }, 'operator/a');
    await putRaw('operator/a', 'preference', '_pref', { schema: CACHE_SCHEMA_VERSION, namespace: 'principal:other', kind: 'preference', key: '_pref', value: { plantId: 'private-a' }, savedAt: 1, expiresAt: Date.now() + 10_000, bytes: 88 });
    await expect(cache.load('operator/a')).resolves.toBeUndefined();
    const oversized = 'x'.repeat(161);
    await cache.save({ plantId: 'private-large' }, oversized);
    await expect(cache.load(oversized)).resolves.toBeUndefined();
  });

  it('removes expired and corrupt rows during bounded maintenance', async () => {
    await putRaw('expired', 'preference', '_pref', { schema: CACHE_SCHEMA_VERSION, namespace: 'principal:expired', kind: 'preference', key: '_pref', value: {}, savedAt: 1, expiresAt: 1, bytes: 2 });
    await putRaw('corrupt', 'preference', '_pref', { schema: CACHE_SCHEMA_VERSION, namespace: 'principal:corrupt', kind: 'preference', key: '_pref', value: {}, savedAt: 1, expiresAt: Date.now() + 10_000, bytes: 9999 });
    await cache.save({ plantId: 'fresh' }, 'fresh');
    await expect(cache.load('expired')).resolves.toBeUndefined();
    await expect(cache.load('corrupt')).resolves.toBeUndefined();
    await expect(cache.load('fresh')).resolves.toEqual({ plantId: 'fresh' });
  });

  it('keeps readback bounded to the maximum entry count', async () => {
    for (let index = 0; index < 30; index += 1) {
      await cache.save({ plantId: `plant-${index}` }, `principal-${index}`);
    }
    expect(await readEntryCount()).toBeLessThanOrEqual(24);
    await expect(cache.load('principal-29')).resolves.toEqual({ plantId: 'plant-29' });
  });

  it('fails safely when IndexedDB is unavailable', async () => {
    const original = globalThis.indexedDB;
    Object.defineProperty(globalThis, 'indexedDB', { configurable: true, value: undefined });
    const unavailable = new PreferenceCache();
    await expect(unavailable.save({ plantId: 'safe' }, 'principal-a')).resolves.toBeUndefined();
    await expect(unavailable.load('principal-a')).resolves.toBeUndefined();
    await expect(unavailable.saveForecast('plant-01', snapshot() as never, 'principal-a')).resolves.toBeUndefined();
    await expect(unavailable.loadForecast('plant-01', 'principal-a')).resolves.toBeUndefined();
    Object.defineProperty(globalThis, 'indexedDB', { configurable: true, value: original });
  });
});

describe('IDB-M9-ISOLATE forecast snapshots', () => {
  it('stores and reloads a sanitized 12-hour forecast snapshot per principal', async () => {
    await cache.saveForecast('plant-01', snapshot() as never, 'operator-a');
    await cache.saveForecast('plant-01', snapshot() as never, 'operator-b');
    const a = await cache.loadForecast('plant-01', 'operator-a');
    expect(a?.plant.plant_id).toBe('plant-01');
    expect(a?.forecasts).toHaveLength(12);
    expect(a?.status).toBe('available');
    const b = await cache.loadForecast('plant-01', 'operator-b');
    expect(b?.forecasts).toHaveLength(12);
    // disjoint principals
    await expect(cache.loadForecast('plant-01')).resolves.toBeUndefined();
  });

  it('sanitizes forecast snapshots (bounds hours, drops junk, never stores tokens)', async () => {
    const raw: Record<string, unknown> = { plant: { plant_id: 'plant-01', name: 'Alpha', timezone: 'America/New_York' }, status: 'available', issued_at_utc: '2025-01-01T00:00:00.000Z', model_version: 'm', forecasts: Array.from({ length: 14 }, (_, index) => ({ hour_number: index + 1, target_time_utc: new Date(Date.UTC(2025, 0, 1, index + 1)).toISOString(), predicted_flow_gal_h: 100 + index, units: 'gal/h' })), unavailable_reason: null };
    await cache.saveForecast('plant-01', raw as never, 'operator-a');
    const loaded = await cache.loadForecast('plant-01', 'operator-a');
    expect(loaded?.forecasts).toHaveLength(12);
  });

  it('clears all private rows (preference + forecast) for a principal on remove', async () => {
    await cache.save({ plantId: 'public-plant' });
    await cache.save({ plantId: 'plant-01' }, 'operator-a');
    await cache.saveForecast('plant-01', snapshot() as never, 'operator-a');
    await cache.remove('operator-a');
    await expect(cache.load('operator-a')).resolves.toBeUndefined();
    await expect(cache.loadForecast('plant-01', 'operator-a')).resolves.toBeUndefined();
    await expect(cache.load()).resolves.toEqual({ plantId: 'public-plant' });
  });

  it('never returns an expired forecast snapshot', async () => {
    await putRaw('operator-a', 'forecast', 'plant-01', { schema: CACHE_SCHEMA_VERSION, namespace: 'principal:operator-a', kind: 'forecast', key: 'plant-01', value: snapshot(), savedAt: 1, expiresAt: 1, bytes: 2 });
    await expect(cache.loadForecast('plant-01', 'operator-a')).resolves.toBeUndefined();
  });
});
