/**
 * Per-principal UI preferences in IndexedDB. Only one storage concern lives here
 * (#33): the authorized forecast snapshot cache was removed (#34) because it was
 * written but never read by production code. This keeps the store small,
 * strictly sanitized, and bounded.
 */

export const CACHE_SCHEMA_VERSION = 3;
const DB_NAME = 'flowstead-preferences';
const STORE_NAME = 'entries';
const MAX_ENTRIES = 24;
const MAX_BYTES = 8_192;
const MAX_PRINCIPAL_ID_LENGTH = 160;
const PREFERENCE_TTL_MS = 30 * 24 * 60 * 60 * 1000;

type Namespace = 'public' | `principal:${string}`;

export interface PreferenceState {
  plantId?: string;
}

interface StoredEntry {
  schema: number;
  namespace: Namespace;
  key: string;
  value: unknown;
  savedAt: number;
  expiresAt: number;
  bytes: number;
}

function namespaceFor(principalId?: string): Namespace | undefined {
  if (!principalId) return 'public';
  if (principalId.length > MAX_PRINCIPAL_ID_LENGTH) return undefined;
  const encoded = encodeURIComponent(principalId);
  if (encoded.length > MAX_PRINCIPAL_ID_LENGTH) return undefined;
  return `principal:${encoded}`;
}
function keyFor(namespace: Namespace): string {
  return `${CACHE_SCHEMA_VERSION}:${namespace}:pref`;
}
function sanitizePreference(value: unknown): PreferenceState {
  const source = value && typeof value === 'object' ? value as Record<string, unknown> : {};
  const result: PreferenceState = {};
  if (typeof source.plantId === 'string' && source.plantId.length <= 160 && /^[a-zA-Z0-9._:-]+$/.test(source.plantId)) result.plantId = source.plantId;
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
function isStoredEntry(value: unknown, key: IDBValidKey): value is StoredEntry {
  if (!value || typeof value !== 'object' || typeof key !== 'string') return false;
  const entry = value as Partial<StoredEntry>;
  if (entry.schema !== CACHE_SCHEMA_VERSION || !isNamespace(entry.namespace)
    || typeof entry.key !== 'string'
    || !entry.value || typeof entry.value !== 'object'
    || typeof entry.savedAt !== 'number' || !Number.isFinite(entry.savedAt)
    || typeof entry.expiresAt !== 'number' || !Number.isFinite(entry.expiresAt)
    || typeof entry.bytes !== 'number' || !Number.isFinite(entry.bytes)
    || entry.bytes < 0 || entry.bytes > MAX_BYTES) return false;
  if (!sanitizePreference(entry.value)) return false;
  return key === keyFor(entry.namespace);
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
    const { promise, resolve, reject } = Promise.withResolvers<Array<{ key: IDBValidKey; entry: unknown }>>();
    const request = db.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).openCursor();
    const result: Array<{ key: IDBValidKey; entry: unknown }> = [];
    request.onsuccess = () => {
      const cursor = request.result;
      if (!cursor) return resolve(result);
      result.push({ key: cursor.primaryKey, entry: cursor.value });
      cursor.continue();
    };
    request.onerror = () => reject(request.error);
    return promise;
  }
  private async deleteKeys(db: IDBDatabase, keys: IDBValidKey[]): Promise<void> {
    if (keys.length === 0) return;
    const { promise, resolve, reject } = Promise.withResolvers<void>();
    const transaction = db.transaction(STORE_NAME, 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    for (const key of keys) store.delete(key);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
    transaction.onabort = () => reject(transaction.error);
    await promise;
  }
  private async getEntry(namespace: Namespace): Promise<StoredEntry | undefined> {
    const db = await this.db(); if (!db) return undefined;
    const storeKey = keyFor(namespace);
    try {
      const { promise, resolve, reject } = Promise.withResolvers<StoredEntry | undefined>();
      const request = db.transaction(STORE_NAME, 'readonly').objectStore(STORE_NAME).get(storeKey);
      request.onsuccess = () => resolve(request.result === undefined ? undefined : request.result as StoredEntry);
      request.onerror = () => reject(request.error);
      const record = await promise;
      if (!record || !isStoredEntry(record, storeKey) || record.namespace !== namespace || record.expiresAt <= Date.now()) {
        if (record) await this.deleteKeys(db, [storeKey]);
        return undefined;
      }
      return record;
    } catch { return undefined; }
  }
  private async putEntry(namespace: Namespace, value: unknown, ttl: number): Promise<void> {
    const db = await this.db(); if (!db) return;
    const storeKey = keyFor(namespace);
    const savedAt = Date.now();
    const entry: StoredEntry = { schema: CACHE_SCHEMA_VERSION, namespace, key: storeKey, value, savedAt, expiresAt: savedAt + ttl, bytes: 0 };
    entry.bytes = serializedEntryBytes(storeKey, entry);
    if (entry.bytes > MAX_BYTES) return;
    try {
      const { promise, resolve, reject } = Promise.withResolvers<void>();
      const transaction = db.transaction(STORE_NAME, 'readwrite');
      transaction.objectStore(STORE_NAME).put(entry, storeKey);
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
      await promise;
      await this.enforceBounds(db);
    } catch { /* IDB is convenience state: UI continues with memory */ }
  }
  async load(principalId?: string): Promise<PreferenceState | undefined> {
    const namespace = namespaceFor(principalId);
    if (!namespace) return undefined;
    const entry = await this.getEntry(namespace);
    if (!entry) return undefined;
    return sanitizePreference(entry.value);
  }
  async save(value: PreferenceState, principalId?: string): Promise<void> {
    const namespace = namespaceFor(principalId);
    if (!namespace) return;
    await this.putEntry(namespace, sanitizePreference(value), PREFERENCE_TTL_MS);
  }
  async remove(principalId?: string): Promise<void> {
    const namespace = namespaceFor(principalId);
    if (!namespace) return;
    const db = await this.db(); if (!db) return;
    try { await this.deleteKeys(db, [keyFor(namespace)]); } catch { /* safe no-op */ }
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
      if (!isNamespace(candidate.namespace) || typeof candidate.key !== 'string') return true;
      if (!isStoredEntry(entry, key)) return true;
      return candidate.expiresAt! <= now;
    });
    await this.deleteKeys(db, staleOrCorrupt.map(({ key }) => key));
    const valid = records.filter((record): record is { key: IDBValidKey; entry: StoredEntry } => {
      if (!record.entry || typeof record.entry !== 'object') return false;
      const candidate = record.entry as Partial<StoredEntry>;
      if (!isStoredEntry(record.entry, record.key)) return false;
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