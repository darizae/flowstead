/**
 * Identity boundary for Flowstead. Supabase Auth supplies identity only; every
 * Plant/data request continues to go to FastAPI. Anonymous mode uses strictly
 * separate public endpoints (the ApiClient routes by presence of a token).
 *
 * Hosted Supabase login is UNVERIFIED: this module is wired to public
 * `.env.example` placeholders, and an offline TestAuthProvider seam drives
 * scripted login/expiry/logout in unit and browser tests.
 */

import { createClient, type SupabaseClient } from '@supabase/supabase-js';

export interface AuthSession {
  token: string;
  principalId: string;
  /** milliseconds since epoch, or null when unknown/never expires */
  expiresAt: number | null;
}

export interface AuthProvider {
  getSession(): AuthSession | null;
  signOut(): Promise<void>;
  subscribe(listener: () => void): () => void;
}

/** Offline, deterministic provider used by unit and browser tests and when no hosted Auth is configured. */
export class TestAuthProvider implements AuthProvider {
  private session: AuthSession | null;
  private readonly listeners = new Set<() => void>();
  constructor(initial?: AuthSession | null) { this.session = initial ?? null; }
  getSession(): AuthSession | null { return this.session; }
  setSession(session: AuthSession | null): void {
    this.session = session;
    for (const listener of this.listeners) listener();
  }
  async signOut(): Promise<void> { this.setSession(null); }
  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  }
}

/**
 * Identity-only Supabase client. Only the public URL and publishable (anon) key
 * are allowed; data always comes from FastAPI. Requires real configured Supabase
 * to produce a session; without it the provider stays signed out (anonymous).
 */
export class SupabaseAuthProvider implements AuthProvider {
  private readonly client: SupabaseClient;
  private readonly listeners = new Set<() => void>();
  private cachedSession: AuthSession | null;
  constructor(supabase: SupabaseClient) {
    this.client = supabase;
    this.cachedSession = null;
    // Identity source; data always flows through FastAPI.
    void supabase.auth.getSession().then(({ data }) => {
      this.cachedSession = this.mapSession(data.session);
      this.emit();
    });
    supabase.auth.onAuthStateChange((_event, session) => {
      this.cachedSession = this.mapSession(session);
      this.emit();
    });
  }
  private mapSession(session: { access_token: string; user?: { id?: string } | null; expires_at?: number | null } | null): AuthSession | null {
    if (!session?.access_token || !session.user?.id) return null;
    return {
      token: session.access_token,
      principalId: session.user.id,
      expiresAt: session.expires_at != null ? session.expires_at * 1000 : null,
    };
  }
  getSession(): AuthSession | null { return this.cachedSession; }
  async signOut(): Promise<void> {
    await this.client.auth.signOut();
    this.cachedSession = null;
    this.emit();
  }
  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  }
  private emit(): void { for (const listener of this.listeners) listener(); }
}

/**
 * Build the app's identity provider from public environment variables. Only the
 * Supabase URL and publishable (anon) key are accepted; hosted Supabase is
 * UNVERIFIED, so missing placeholders fall back to the offline test seam.
 */
/** Test-only injected seam (set by Playwright/DOM tests before app load). */
export interface FlowsteadTestAuthGlobal { __FLOWSTEAD_TEST_AUTH__?: AuthProvider }

export function createDefaultAuthProvider(): AuthProvider {
  const injected = (globalThis as FlowsteadTestAuthGlobal).__FLOWSTEAD_TEST_AUTH__;
  if (injected) return injected;
  const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
  const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;
  if (url && anonKey) {
    try {
      return new SupabaseAuthProvider(createClient(url, anonKey));
    } catch {
      /* fall back to offline seam */
    }
  }
  return new TestAuthProvider();
}

