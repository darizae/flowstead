import type { ForecastResponse } from '../api/types';

export const CACHE_SCHEMA_VERSION = 2;
const DB_NAME = 'flowstead-preferences';
const STORE_NAME = 'entries';
const MAX_ENTRIES = 24;
const MAX_BYTES = 8_192;
const MAX_PRINCIPAL_ID_LENGTH = 160;
const PREFERENCE_TTL_MS = 30 * 24 * 60 * 60 * 1000;
// Fresh FastAPI authorization is required before a snapshot is trusted; this
// TTL is intentionally short so offline caches never outlive reauthorization.
const SNAPSHOT_TTL_MS = 6 * 60 * 60 * 1000;
const MAX_FORECAST_HOURS = 12;
const FORECAST_PLANT_ID_LENGTH = 160;

type Namespace = 'public' | `principal:${string}`;
type EntryKind = 'preference' | 'forecast';

export interface PreferenceState {
  plantId?: string;
  chart?: 'influent_flow' | 'rainfall' | 'dissolved_oxygen' | 'effluent_ph';
  windowHours?: 24 | 72 | 168;
}

/** Small sanitized forecast snapshot persisted only after verified FastAPI authorization. */
export interface ForecastSnapshot {
  plant: { plant_id: string; name: string; timezone: string };
  status: 'available' | 'unavailable';
  issued_at_utc: string | null;
  model_version: string;
  forecasts: Array<{ hour_number: number; target_time_utc: string; predicted_flow_gal_h: number; units: 'gal/h' }>;
  unavailable_reason: string | null;
}

interface StoredEntry {
  schema: number;
  namespace: Namespace;
  kind: EntryKind;
  key: string;
  value: unknown;
  savedAt: number;
  expiresAt: number;
  bytes: number;
}

const charts = new Set(['influent_flow', 'rainfall', 'dissolved_oxygen', 'effluent_ph']);
const windows = new Set([24, 72, 168]);

function namespaceFor(principalId?: string): Namespace | undefined {
  if (!principalId) return 'public';
  if (principalId.length > MAX_PRINCIPAL_ID_LENGTH) return undefined;
  const encoded = encodeURIComponent(principalId);
  if (encoded.length > MAX_PRINCIPAL_ID_LENGTH) return undefined;
  return `principal:${encoded}`;
}
function keyFor(namespace: Namespace, kind: EntryKind, key: string): string {
  return `${CACHE_SCHEMA_VERSION}:${namespace}:${kind}:${key}`;
}
function sanitizePreference(value: unknown): PreferenceState {
  const source = value && typeof value === 'object' ? value as Record<string, unknown> : {};
  const result: PreferenceState = {};
  if (typeof source.plantId === 'string' && source.plantId.length <= 160 && /^[a-zA-Z0-9._:-]+$/.test(source.plantId)) result.plantId = source.plantId;
  if (typeof source.chart === 'string' && charts.has(source.chart)) result.chart = source.chart as PreferenceState['chart'];
  if (typeof source.windowHours === 'number' && windows.has(source.windowHours)) result.windowHours = source.windowHours as PreferenceState['windowHours'];
  return result;
}
function sanitizeForecast(value: unknown): ForecastSnapshot | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const source = value as Record<string, unknown>;
  const plant = source.plant && typeof source.plant === 'object' ? source.plant as Record<string, unknown> : {};
  if (typeof plant.plant_id !== 'string' || !plant.plant_id || plant.plant_id.length > FORECAST_PLANT_ID_LENGTH) return undefined;
  const status = source.status;
  if (status !== 'available' && status !== 'unavailable') return undefined;
  const forecasts: ForecastSnapshot['forecasts'] = [];
  const rawHours = Array.isArray(source.forecasts) ? source.forecasts.slice(0, MAX_FORECAST_HOURS) : [];
  for (const raw of rawHours) {
    if (!raw || typeof raw !== 'object') continue;
    const hour = raw as Record<string, unknown>;
    const number = hour.hour_number;
    if (typeof number !== 'number' || !Number.isInteger(number) || number < 1 || number > 12) continue;
    if (typeof hour.target_time_utc !== 'string' || !Number.isFinite(Date.parse(hour.target_time_utc))) continue;
    if (typeof hour.predicted_flow_gal_h !== 'number' || !Number.isFinite(hour.predicted_flow_gal_h) || hour.predicted_flow_gal_h < 0) continue;
    forecasts.push({ hour_number: number, target_time_utc: hour.target_time_utc, predicted_flow_gal_h: hour.predicted_flow_gal_h, units: 'gal/h' });
  }
  const issuedAt = typeof source.issued_at_utc === 'string' && Number.isFinite(Date.parse(source.issued_at_utc)) ? source.issued_at_utc : null;
  const unavailableReason = typeof source.unavailable_reason === 'string' && source.unavailable_reason.length <= 400 ? source.unavailable_reason : null;
  const modelVersion = typeof source.model_version === 'string' && source.model_version.length <= 200 ? source.model_version : '';
  return {
    plant: { plant_id: plant.plant_id, name: typeof plant.name === 'string' ? plant.name.slice(0, 200) : '', timezone: typeof plant.timezone === 'string' ? plant.timezone.slice(0, 100) : '' },
    status,
    issued_at_utc: issuedAt,
    model_version: modelVersion,
    forecasts,
    unavailable_reason: unavailableReason,
  };
}
function encodedBytes(value: unknown): number {
  const serialized = JSON.stringify(value);
  if (typeof serialized !== 'string') throw new TypeError('value is not serializable');
  return new TextEncoder().encode(serialized).byteLength;
}
function isNamespace(value: unknown): value is Namespace {
  return value === 'public' || (typeof value === 'string' && value.startsWith('principal:'));
}
function isStoredEntry(value: unknown, key: IDBValidKey, expectedKind: EntryKind): value is StoredEntry {
  if (!value || typeof value !== 'object' || typeof key !== 'string') return false;
  const entry = value as Partial<StoredEntry>;
  if (entry.schema !== CACHE_SCHEMA_VERSION || !isNamespace(entry.namespace)
    || (entry.kind !== 'preference' && entry.kind !== 'forecast')
    || entry.kind !== expectedKind
    || typeof entry.key !== 'string'
    || !entry.value || typeof entry.value !== 'object'
    || typeof entry.savedAt !== 'number' || !Number.isFinite(entry.savedAt)
    || typeof entry.expiresAt !== 'number' || !Number.isFinite(entry.expiresAt)
    || typeof entry.bytes !== 'number' || !Number.isFinite(entry.bytes)
    || entry.bytes < 0 || entry.bytes > MAX_BYTES) return false;
  if (entry.kind === 'preference' && !sanitizePreference(entry.value)) return false;
  if (entry.kind === 'forecast' && !sanitizeForecast(entry.value)) return false;
  return key === keyFor(entry.namespace, entry.kind, entry.key);
}
function serializedEntryBytes(key: string, entry: StoredEntry): number {
  let bytes = entry.bytes;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const next = encodedBytes({ key, entry: { ...entry, bytes } });
    if (next === bytes) return next;
    bytes = next;
  }
  return bytes;
}

export class PreferenceCache {
  private dbPromise?: Promise<IDBDatabase | undefined>;
  private db(): Promise<IDBDatabase | undefined> {
    if (this.dbPromise) return this.dbPromise;
    this.dbPromise = new Promise((resolve) => {
      if (typeof indexedDB === 'undefined') return resolve(undefined);
      let request: IDBOpenDBRequest;
      try { request = indexedDB.open(DB_NAME, CACHE_SCHEMA_VERSION); }
      catch { return resolve(undefined); }
      request.onupgradeneeded = () => {
        try {
          const db = request.result;
          if (!db.objectStoreNames.contains(STORE_NAME)) db.createObjectStore(STORE_NAME);
        } catch { resolve(undefined); }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => resolve(undefined);
      request.onblocked = () => resolve(undefined);
    });
    return this.dbPromise;
  }
  private async entries(db: IDBDatabase): Promise<Array<{ key: IDBValidKey; entry: unknown }>> {
    return new Promise((resolve, reject) => {
      const request = db.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).openCursor();
      const result: Array<{ key: IDBValidKey; entry: unknown }> = [];
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) return resolve(result);
        result.push({ key: cursor.primaryKey, entry: cursor.value });
        cursor.continue();
      };
      request.onerror = () => reject(request.error);
    });
  }
  private async deleteKeys(db: IDBDatabase, keys: IDBValidKey[]): Promise<void> {
    if (keys.length === 0) return;
    await new Promise<void>((resolve, reject) => {
      const transaction = db.transaction(STORE_NAME, 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      for (const key of keys) store.delete(key);
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
  }
  private async getEntry(namespace: Namespace, kind: EntryKind, key: string): Promise<StoredEntry | undefined> {
    const db = await this.db(); if (!db) return undefined;
    const storeKey = keyFor(namespace, kind, key);
    try {
      const record = await new Promise<StoredEntry | undefined>((resolve, reject) => {
        const request = db.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).get(storeKey);
        request.onsuccess = () => resolve(request.result === undefined ? undefined : request.result as StoredEntry);
        request.onerror = () => reject(request.error);
      });
      if (!record || !isStoredEntry(record, storeKey, kind) || record.namespace !== namespace || record.expiresAt <= Date.now()) {
        if (record) await this.deleteKeys(db, [storeKey]);
        return undefined;
      }
      return record;
    } catch { return undefined; }
  }
  private async putEntry(namespace: Namespace, kind: EntryKind, key: string, value: unknown, ttl: number): Promise<void> {
    const db = await this.db(); if (!db) return;
    const storeKey = keyFor(namespace, kind, key);
    const savedAt = Date.now();
    const entry: StoredEntry = { schema: CACHE_SCHEMA_VERSION, namespace, kind, key, value, savedAt, expiresAt: savedAt + ttl, bytes: 0 };
    entry.bytes = serializedEntryBytes(storeKey, entry);
    if (entry.bytes > MAX_BYTES) return;
    try {
      await new Promise<void>((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readwrite');
        transaction.objectStore(STORE_NAME).put(entry, storeKey);
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(transaction.error);
        transaction.onabort = () => reject(transaction.error);
      });
      await this.enforceBounds(db);
    } catch { /* IDB is convenience state: UI continues with memory */ }
  }
  async load(principalId?: string): Promise<PreferenceState | undefined> {
    const namespace = namespaceFor(principalId);
    if (!namespace) return undefined;
    const entry = await this.getEntry(namespace, 'preference', '_pref');
    if (!entry) return undefined;
    return sanitizePreference(entry.value);
  }
  async save(value: PreferenceState, principalId?: string): Promise<void> {
    const namespace = namespaceFor(principalId);
    if (!namespace) return;
    await this.putEntry(namespace, 'preference', '_pref', sanitizePreference(value), PREFERENCE_TTL_MS);
  }
  async saveForecast(plantId: string, value: ForecastResponse, principalId?: string): Promise<void> {
    const namespace = namespaceFor(principalId);
    if (!namespace || !plantId || plantId.length > FORECAST_PLANT_ID_LENGTH) return;
    const snapshot = sanitizeForecast(value);
    if (!snapshot) return;
    await this.putEntry(namespace, 'forecast', plantId, snapshot, SNAPSHOT_TTL_MS);
  }
  async loadForecast(plantId: string, principalId?: string): Promise<ForecastSnapshot | undefined> {
    const namespace = namespaceFor(principalId);
    if (!namespace || !plantId || plantId.length > FORECAST_PLANT_ID_LENGTH) return undefined;
    const entry = await this.getEntry(namespace, 'forecast', plantId);
    if (!entry) return undefined;
    const snapshot = sanitizeForecast(entry.value);
    return snapshot;
  }
  async remove(principalId?: string): Promise<void> {
    const namespace = namespaceFor(principalId);
    if (!namespace) return;
    const db = await this.db(); if (!db) return;
    try { await this.deleteKeys(db, [keyFor(namespace, 'preference', '_pref')]); } catch { /* safe no-op */ }
    try { await this.dropNamespace(db, namespace); } catch { /* safe no-op */ }
  }
  async clearPrivate(): Promise<void> {
    const db = await this.db(); if (!db) return;
    try {
      const records = await this.entries(db);
      const keys = records.filter(({ entry }) => {
        if (!entry || typeof entry !== 'object' || !('namespace' in entry)) return false;
        const namespace = entry.namespace;
        return typeof namespace === 'string' && namespace.startsWith('principal:');
      }).map(({ key }) => key);
      await this.deleteKeys(db, keys);
    } catch { /* safe no-op */ }
  }
  private async dropNamespace(db: IDBDatabase, namespace: Namespace): Promise<void> {
    const records = await this.entries(db);
    const keys = records.filter(({ entry }) => {
      if (!entry || typeof entry !== 'object' || !('namespace' in entry)) return false;
      return entry.namespace === namespace;
    }).map(({ key }) => key);
    await this.deleteKeys(db, keys);
  }
  private async enforceBounds(db: IDBDatabase): Promise<void> {
    const now = Date.now();
    const records = await this.entries(db);
    const staleOrCorrupt = records.filter(({ key, entry }) => {
      if (!entry || typeof entry !== 'object') return true;
      const candidate = entry as Partial<StoredEntry>;
      if (candidate.schema !== CACHE_SCHEMA_VERSION) return true;
      if (!isNamespace(candidate.namespace) || (candidate.kind !== 'preference' && candidate.kind !== 'forecast') || typeof candidate.key !== 'string') return true;
      if (!isStoredEntry(entry, key, candidate.kind)) return true;
      return candidate.expiresAt! <= now;
    });
    await this.deleteKeys(db, staleOrCorrupt.map(({ key }) => key));
    const valid = records.filter((record): record is { key: IDBValidKey; entry: StoredEntry } => {
      if (!record.entry || typeof record.entry !== 'object') return false;
      const candidate = record.entry as Partial<StoredEntry>;
      if (!isStoredEntry(record.entry, record.key, candidate.kind!)) return false;
      return candidate.expiresAt! > now;
    }).sort((left, right) => left.entry.savedAt - right.entry.savedAt);
    let remainingCount = valid.length;
    let total = valid.reduce((sum, { entry }) => sum + entry.bytes, 0);
    const evicted: IDBValidKey[] = [];
    for (const { key, entry } of valid) {
      if (remainingCount <= MAX_ENTRIES && total <= MAX_BYTES) break;
      evicted.push(key);
      remainingCount -= 1;
      total -= entry.bytes;
    }
    await this.deleteKeys(db, evicted);
  }
}

export const preferences = new PreferenceCache();
