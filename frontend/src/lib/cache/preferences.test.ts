import 'fake-indexeddb/auto';
import { beforeEach, describe, expect, it } from 'vitest';
import { CACHE_SCHEMA_VERSION, PreferenceCache } from './preferences';

const cache = new PreferenceCache();
const entryKey = (principal: string) => `${CACHE_SCHEMA_VERSION}:principal:${encodeURIComponent(principal)}:pref`;

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

async function putRaw(principal: string, entry: Record<string, unknown>): Promise<void> {
  const database = await new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open('flowstead-preferences', CACHE_SCHEMA_VERSION);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  const { promise, resolve, reject } = Promise.withResolvers<void>();
  const transaction = database.transaction('entries', 'readwrite');
  transaction.objectStore('entries').put(entry, entryKey(principal));
  transaction.oncomplete = () => { database.close(); resolve(); };
  transaction.onerror = () => reject(transaction.error);
  await promise;
}

beforeEach(async () => {
  await cache.clearPrivate();
  await cache.remove();
});

describe('PreferenceCache', () => {
  it('sanitizes unsupported plantId values before persistence', async () => {
    await cache.save({ plantId: '<script>' }, 'principal/a');
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
    await putRaw('operator/a', { schema: CACHE_SCHEMA_VERSION, namespace: 'principal:other', key: '_pref', value: { plantId: 'private-a' }, savedAt: 1, expiresAt: Date.now() + 10_000, bytes: 88 });
    await expect(cache.load('operator/a')).resolves.toBeUndefined();
    const oversized = 'x'.repeat(161);
    await cache.save({ plantId: 'private-large' }, oversized);
    await expect(cache.load(oversized)).resolves.toBeUndefined();
  });

  it('removes expired and corrupt rows during bounded maintenance', async () => {
    await putRaw('expired', { schema: CACHE_SCHEMA_VERSION, namespace: 'principal:expired', key: '_pref', value: {}, savedAt: 1, expiresAt: 1, bytes: 2 });
    await putRaw('corrupt', { schema: CACHE_SCHEMA_VERSION, namespace: 'principal:corrupt', key: '_pref', value: {}, savedAt: 1, expiresAt: Date.now() + 10_000, bytes: 9999 });
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
    Object.defineProperty(globalThis, 'indexedDB', { configurable: true, value: original });
  });
});