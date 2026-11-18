export const CACHE_SCHEMA_VERSION = 1;
const DB_NAME = 'flowstead-preferences';
const STORE_NAME = 'entries';
const MAX_ENTRIES = 24;
const MAX_BYTES = 8_192;
const MAX_PRINCIPAL_ID_LENGTH = 160;
const TTL_MS = 30 * 24 * 60 * 60 * 1000;

type Namespace = 'public' | `principal:${string}`;
export interface PreferenceState {
  plantId?: string;
  chart?: 'influent_flow' | 'rainfall' | 'dissolved_oxygen' | 'effluent_ph';
  windowHours?: 24 | 72 | 168;
}
interface StoredPreference {
  schema: number;
  namespace: Namespace;
  value: PreferenceState;
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
function keyFor(namespace: Namespace): string { return `${CACHE_SCHEMA_VERSION}:${namespace}`; }
function sanitize(value: unknown): PreferenceState {
  const source = value && typeof value === 'object' ? value as Record<string, unknown> : {};
  const result: PreferenceState = {};
  if (typeof source.plantId === 'string' && source.plantId.length <= 160 && /^[a-zA-Z0-9._:-]+$/.test(source.plantId)) result.plantId = source.plantId;
  if (typeof source.chart === 'string' && charts.has(source.chart)) result.chart = source.chart as PreferenceState['chart'];
  if (typeof source.windowHours === 'number' && windows.has(source.windowHours)) result.windowHours = source.windowHours as PreferenceState['windowHours'];
  return result;
}
function encodedBytes(value: unknown): number {
  const serialized = JSON.stringify(value);
  if (typeof serialized !== 'string') throw new TypeError('value is not serializable');
  return new TextEncoder().encode(serialized).byteLength;
}
function isNamespace(value: unknown): value is Namespace {
  return value === 'public' || (typeof value === 'string' && value.startsWith('principal:'));
}
function serializedEntryBytes(key: string, entry: StoredPreference): number {
  let bytes = entry.bytes;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const next = encodedBytes({ key, entry: { ...entry, bytes } });
    if (next === bytes) return next;
    bytes = next;
  }
  return bytes;
}
function isStoredPreference(value: unknown, key: IDBValidKey): value is StoredPreference {
  if (!value || typeof value !== 'object' || typeof key !== 'string') return false;
  const entry = value as Partial<StoredPreference>;
  if (entry.schema !== CACHE_SCHEMA_VERSION || !isNamespace(entry.namespace)
    || !entry.value || typeof entry.value !== 'object'
    || typeof entry.savedAt !== 'number' || !Number.isFinite(entry.savedAt)
    || typeof entry.expiresAt !== 'number' || !Number.isFinite(entry.expiresAt)
    || typeof entry.bytes !== 'number' || !Number.isFinite(entry.bytes)
    || entry.bytes < 0 || entry.bytes > MAX_BYTES) return false;
  try {
    return key === keyFor(entry.namespace) && serializedEntryBytes(key, entry as StoredPreference) === entry.bytes;
  } catch { return false; }
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
  async load(principalId?: string): Promise<PreferenceState | undefined> {
    const namespace = namespaceFor(principalId);
    if (!namespace) return undefined;
    const db = await this.db(); if (!db) return undefined;
    const key = keyFor(namespace);
    try {
      const record = await new Promise<{ key: IDBValidKey; entry: unknown } | undefined>((resolve, reject) => {
        const request = db.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).get(key);
        request.onsuccess = () => resolve(request.result === undefined ? undefined : { key, entry: request.result });
        request.onerror = () => reject(request.error);
      });
      if (!record || !isStoredPreference(record.entry, record.key) || record.entry.namespace !== namespace || record.entry.expiresAt <= Date.now()) {
        if (record) await this.deleteKeys(db, [record.key]);
        return undefined;
      }
      return sanitize(record.entry.value);
    } catch { return undefined; }
  }
  async save(value: PreferenceState, principalId?: string): Promise<void> {
    const namespace = namespaceFor(principalId);
    if (!namespace) return;
    const db = await this.db(); if (!db) return;
    const clean = sanitize(value);
    const key = keyFor(namespace);
    const savedAt = Date.now();
    const entry: StoredPreference = { schema: CACHE_SCHEMA_VERSION, namespace, value: clean, savedAt, expiresAt: savedAt + TTL_MS, bytes: 0 };
    entry.bytes = serializedEntryBytes(key, entry);
    if (entry.bytes > MAX_BYTES) return;
    try {
      await new Promise<void>((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readwrite');
        transaction.objectStore(STORE_NAME).put(entry, key);
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(transaction.error);
        transaction.onabort = () => reject(transaction.error);
      });
      await this.enforceBounds(db);
    } catch { /* IDB is convenience state: UI continues with memory */ }
  }
  async remove(principalId?: string): Promise<void> {
    const namespace = namespaceFor(principalId);
    if (!namespace) return;
    const db = await this.db(); if (!db) return;
    try { await this.deleteKeys(db, [keyFor(namespace)]); } catch { /* safe no-op */ }
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
  private async enforceBounds(db: IDBDatabase): Promise<void> {
    const now = Date.now();
    const records = await this.entries(db);
    const staleOrCorrupt = records.filter(({ key, entry }) => {
      if (!isStoredPreference(entry, key)) return true;
      return entry.expiresAt <= now;
    });
    await this.deleteKeys(db, staleOrCorrupt.map(({ key }) => key));
    const valid = records.filter((record): record is { key: IDBValidKey; entry: StoredPreference } => {
      if (!isStoredPreference(record.entry, record.key)) return false;
      return record.entry.expiresAt > now;
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
