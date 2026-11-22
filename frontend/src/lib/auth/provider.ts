/**
 * Identity boundary for Flowstead. Supabase Auth supplies identity only; every
 * Plant/data request continues to go to FastAPI. Anonymous mode uses strictly
 * separate public endpoints (the ApiClient routes by presence of a token).
 *
 * Hosted Supabase login is UNVERIFIED: this module is wired to public
 * `.env.example` placeholders. When Supabase is unconfigured the provider FAILS
 * CLOSED (#39) rather than falling back to the TestAuthProvider test seam,
 * which unit and browser tests inject explicitly.
 */

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

export interface AuthSession {
  token: string;
  principalId: string;
  /** milliseconds since epoch, or null when unknown/never expires */
  expiresAt: number | null;
}

export interface AuthProvider {
  getSession(): AuthSession | null;
  /**
   * Email/password sign-in. Must reject rather than fabricate an identity when
   * the provider cannot authenticate the user (offline seam, missing config).
   */
  signIn?(email: string, password: string): Promise<AuthSession | null>;
  signOut(): Promise<void>;
  subscribe(listener: () => void): () => void;
}

/** Offline, deterministic provider used by unit and browser tests and when no hosted Auth is configured. */
export class TestAuthProvider implements AuthProvider {
  private session: AuthSession | null;
  private readonly listeners = new Set<() => void>();
  /**
   * @param enroll Test-only opt-in: when set, signIn() accepts the supplied
   * credentials as a simulated session. Defaults to reject-all so the offline
   * live default stays fail-closed (no fabricated identity).
   */
  constructor(
    initial?: AuthSession | null,
    private readonly enroll?: {
      email: string;
      password: string;
      principalId: string;
    },
  ) {
    this.session = initial ?? null;
  }
  getSession(): AuthSession | null {
    return this.session;
  }
  async signIn(email: string, password: string): Promise<AuthSession | null> {
    if (
      !this.enroll ||
      this.enroll.email !== email ||
      this.enroll.password !== password
    ) {
      throw new Error("Sign in unavailable. Contact your administrator.");
    }
    this.setSession({
      token: `TOKEN-${this.enroll.principalId}`,
      principalId: this.enroll.principalId,
      expiresAt: Date.now() + 10 * 60 * 1000,
    });
    return this.session;
  }
  setSession(session: AuthSession | null): void {
    this.session = session;
    for (const listener of this.listeners) listener();
  }
  async signOut(): Promise<void> {
    this.setSession(null);
  }
  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
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
  private mapSession(
    session: {
      access_token: string;
      user?: { id?: string } | null;
      expires_at?: number | null;
    } | null,
  ): AuthSession | null {
    if (!session?.access_token || !session.user?.id) return null;
    return {
      token: session.access_token,
      principalId: session.user.id,
      expiresAt: session.expires_at != null ? session.expires_at * 1000 : null,
    };
  }
  getSession(): AuthSession | null {
    return this.cachedSession;
  }
  async signIn(email: string, password: string): Promise<AuthSession | null> {
    const { data, error } = await this.client.auth.signInWithPassword({
      email,
      password,
    });
    if (error) throw error;
    this.cachedSession = this.mapSession(data.session);
    this.emit();
    return this.cachedSession;
  }
  async signOut(): Promise<void> {
    await this.client.auth.signOut();
    this.cachedSession = null;
    this.emit();
  }
  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }
  private emit(): void {
    for (const listener of this.listeners) listener();
  }
}

/**
 * Build the app's identity provider from public environment variables. Only the
 * Supabase URL and publishable (anon) key are accepted. When hosted Supabase is
 * not configured (or config is malformed) the provider FAILS CLOSED: it never
 * fabricates an identity and always rejects sign-in, so a misconfigured
 * deployment cannot silently hand out a session. The offline TestAuthProvider
 * seam is never the production default (#39); tests inject it explicitly via
 * `__FLOWSTEAD_TEST_AUTH__` or the `auth` prop.
 */

/**
 * Fail-closed identity provider used whenever hosted Supabase is not
 * configured. Always signed out; sign-in always rejects. Distinguishable from
 * TestAuthProvider so a production bundle can never rely on the test seam.
 */
export class FailClosedAuthProvider implements AuthProvider {
  private readonly listeners = new Set<() => void>();
  getSession(): AuthSession | null {
    return null;
  }
  async signIn(_email: string, _password: string): Promise<AuthSession | null> {
    throw new Error("Sign in unavailable. Contact your administrator.");
  }
  async signOut(): Promise<void> {
    /* no session */
  }
  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }
}

/** Test-only injected seam (set by Playwright/DOM tests before app load). */
export interface FlowsteadTestAuthGlobal {
  __FLOWSTEAD_TEST_AUTH__?: AuthProvider;
}

export function createDefaultAuthProvider(): AuthProvider {
  const injected = (globalThis as FlowsteadTestAuthGlobal)
    .__FLOWSTEAD_TEST_AUTH__;
  if (injected) return injected;
  const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
  const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;
  if (url && anonKey) {
    try {
      return new SupabaseAuthProvider(createClient(url, anonKey));
    } catch {
      /* malformed config: fail closed below */
    }
  }
  return new FailClosedAuthProvider();
}
