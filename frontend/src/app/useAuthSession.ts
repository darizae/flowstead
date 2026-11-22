import { useEffect, useState } from 'react';
import type { ApiClient } from '../lib/api/client';
import { preferences } from '../lib/cache/preferences';
import type { AuthProvider, AuthSession } from '../lib/auth/provider';

/**
 * Owns authentication orchestration (#27): session state, token synchronization
 * with the API client, provider subscription, and auth-failure cache clearing.
 */
export function useAuthSession(provider: AuthProvider, usingAuth: boolean, principalIdProp: string | undefined, client: ApiClient) {
  const [authSession, setAuthSession] = useState<AuthSession | null>(() => {
    const session = provider.getSession();
    if (session) client.setToken(session.token); else client.clearToken();
    return session;
  });
  const [notice, setNotice] = useState<string | null>(null);
  const [signInOpen, setSignInOpen] = useState(false);
  const providerPrincipal = authSession?.principalId;
  const principalId = usingAuth ? providerPrincipal : (principalIdProp ?? providerPrincipal);

  const openSignIn = () => setSignInOpen(true);
  const closeSignIn = () => setSignInOpen(false);

  const submitSignIn = async (email: string, password: string): Promise<boolean> => {
    if (!provider.signIn || !email || !password) return false;
    try {
      await provider.signIn(email, password);
      closeSignIn();
      return true;
    } catch {
      return false;
    }
  };

  const signOut = () => { setNotice(null); void provider.signOut(); };

  useEffect(() => {
    if (authSession) client.setToken(authSession.token); else client.clearToken();
  }, [client, authSession]);

  useEffect(() => {
    return provider.subscribe(() => {
      const next = provider.getSession();
      if (next) { client.setToken(next.token); setNotice(null); } else client.clearToken();
      setAuthSession(next);
    });
  }, [client, provider]);

  useEffect(() => {
    client.setAuthFailureHandler((status) => {
      if (status === 401) {
        setNotice('Session expired');
        void provider.signOut().then(() => void preferences.clearPrivate());
      } else {
        // revoked plant 403: wipe private caches so no stale snapshot leaks.
        void preferences.clearPrivate();
      }
    });
    return () => client.setAuthFailureHandler(undefined);
  }, [client, provider]);

  return { authSession, principalId, notice, signInOpen, openSignIn, closeSignIn, submitSignIn, signOut };
}