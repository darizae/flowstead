import 'fake-indexeddb/auto';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiClient } from '../lib/api/client';
import { preferences } from '../lib/cache/preferences';
import { TestAuthProvider, type AuthSession } from '../lib/auth/provider';
import FlowsteadApp from './App';

const anonymousFetcher = () => makeFetcher({ 'principal-a': ['a'] });

const plant = (id: string, name: string) => ({ plant_id: id, name, location: { city: 'Test City', state_code: 'FL' as const, latitude: 27, longitude: -81 }, timezone: 'America/New_York', links: { latest: '', history: '', forecast: '' } });
const latest = (id: string) => ({ latest: true as const, plant: plant(id, 'Alpha Plant'), reading: { plant_id: id, timestamp_utc: '2025-01-01T00:00:00Z', latest: true as const, measurements: { influent_flow: { value: 10, quality: 'valid' as const, units: 'gal/h' as const }, rainfall: { value: null, quality: 'missing' as const, units: 'in/h' as const }, dissolved_oxygen: { value: 2, quality: 'invalid' as const, units: 'mg/L' as const }, effluent_ph: { value: 7, quality: 'valid' as const, units: 'unitless' as const } } } });

describe('Plants navigation', () => {
  it('production offers an explicit, reversible offline mock preview without calling the API for preview rows', async () => {
    vi.stubEnv('PROD', true);
    try {
      window.history.replaceState({}, '', '/plants');
      const fetcher = vi.fn<typeof fetch>().mockRejectedValue(new TypeError('offline'));
      render(<FlowsteadApp client={new ApiClient({ fetcher })} />);
      await screen.findByText('Plants unavailable');
      await userEvent.click(screen.getByRole('button', { name: 'Load Mock Data' }));
      expect(await screen.findByText('Bayview Water Reclamation')).toBeInTheDocument();
      expect(screen.getByText(/MOCK PREVIEW/)).toBeInTheDocument();
      const map = await screen.findByTestId('mock-geographic-map');
      expect(map.querySelector('svg path')).toHaveAttribute('d', expect.stringMatching(/^M[\d.,\s]+Z$/));
      await userEvent.click(screen.getByRole('button', { name: 'Open Bayview Water Reclamation' }));
      expect(await screen.findByText(/Preview only: synthetic browser-generated/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Download PDF' })).toBeDisabled();
      await userEvent.click(screen.getByRole('button', { name: 'Return to Live Data' }));
      await screen.findByText('Plants unavailable');
      expect(screen.queryByText('Bayview Water Reclamation')).not.toBeInTheDocument();
      expect(screen.queryByTestId('mock-geographic-map')).not.toBeInTheDocument();
    } finally {
      vi.unstubAllEnvs();
    }
  });
  it('UT-M7-NAV renders API Plants and supports detail/back without demo rows', async () => {
    window.history.replaceState({}, '', '/plants');
    const fetcher = vi.fn<typeof fetch>().mockImplementation(async (url) => new Response(JSON.stringify(String(url).endsWith('/latest') ? latest('a') : { plants: [plant('a', 'Alpha Plant')] }), { status: 200 }));
    render(<FlowsteadApp client={new ApiClient({ fetcher })} />);
    expect(await screen.findByText('Alpha Plant')).toBeInTheDocument();
    expect(screen.getByTestId('marisma-scope')).toHaveAttribute('data-marisma-accent', 'reedwater');
    expect(screen.getByTestId('marisma-scope')).toHaveAttribute('data-marisma-mode', 'light');
    expect(screen.getByRole('button', { name: /Alpha Plant/ })).toHaveClass('plant-row');
    expect(screen.getByRole('link', { name: 'Plants' })).toHaveAttribute('aria-current', 'page');
    await userEvent.click(screen.getByRole('button', { name: /Alpha Plant/ }));
    expect(await screen.findByRole('heading', { name: 'Measurement history' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Download PDF' })).toBeEnabled();
    await userEvent.click(screen.getByRole('button', { name: /All plants/ }));
    expect(await screen.findByRole('heading', { name: 'Plant list' })).toBeInTheDocument();
  });

  it('UT-M7-FAIL handles empty and inaccessible direct links without leaking Plant data', async () => {
    window.history.replaceState({}, '', '/plants/foreign');
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ plants: [] }), { status: 200 }));
    render(<FlowsteadApp client={new ApiClient({ fetcher })} />);
    expect(await screen.findByText('Plant not available')).toBeInTheDocument();
    expect(screen.queryByText('foreign')).not.toBeInTheDocument();
  });

  it('UT-M7-FAIL offers retry for an API error', async () => {
    window.history.replaceState({}, '', '/plants');
    const fetcher = vi.fn<typeof fetch>().mockRejectedValue(new TypeError('offline'));
    render(<FlowsteadApp client={new ApiClient({ fetcher })} />);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument());
    expect(screen.getByRole('alert')).toHaveTextContent('Plants unavailable');
  });
});

function forecastResponse(id: string) {
  return { plant: plant(id, 'Alpha Plant'), status: 'available', issued_at_utc: '2025-01-01T00:00:00.000Z', model_version: 'seasonal-naive-24h', source_revision: 'abc', physical_bound_rule: 'non-negative', forecasts: Array.from({ length: 12 }, (_, i) => ({ hour_number: i + 1, target_time_utc: new Date(Date.UTC(2025, 0, 1, i + 1)).toISOString(), predicted_flow_gal_h: 100 + i, units: 'gal/h', source: 'seasonal_naive_24h' })), unavailable_reason: null };
}
function historyResponse() { return { plant: plant('a', 'Alpha Plant'), from_utc: '2024-12-31T00:00:00.000Z', to_utc: '2025-01-01T00:00:00.000Z', readings: [] }; }

function makeFetcher(assignments: Record<string, string[]>) {
  const tokenToPrincipal: Record<string, string> = {};
  for (const [principal] of Object.entries(assignments)) {
    tokenToPrincipal[`TOKEN-${principal}`] = principal;
  }
  return vi.fn<typeof fetch>().mockImplementation(async (input, init) => {
    const url = typeof input === 'string' ? input : input.toString();
    const auth = new Headers(init?.headers).get('Authorization') ?? '';
    const token = auth.startsWith('Bearer ') ? auth.slice(7) : null;
    const principal = token ? tokenToPrincipal[token] : undefined;
    const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
    if (url.endsWith('/latest')) return json(latest(url.split('/').slice(-2)[0]));
    if (url.includes('/history')) return json(historyResponse());
    if (url.includes('/forecast')) {
      const id = url.split('/').filter(Boolean).reverse()[1];
      // deny access to plants not assigned to this principal
      if (principal && assignments[principal] && !assignments[principal].includes(id)) {
        return new Response(JSON.stringify({ detail: { code: 'plant_not_found' } }), { status: 404 });
      }
      return json(forecastResponse(id));
    }
    if (url.includes('/plants') && !url.includes('/public')) {
      const allowed = principal ? assignments[principal] ?? [] : [];
      return json({ plants: allowed.map((id) => plant(id, `Plant ${id}`)) });
    }
    return json({ plants: [plant('a', 'Alpha Plant')] });
  });
}

afterEach(async () => {
  await preferences.clearPrivate();
  await preferences.remove();
  window.history.replaceState({}, '', '/plants');
});

describe('UT-M9-SESSIONS', () => {
  it('logged-out mode shows Sign in entry, no Sign out, and no open-signup CTA', async () => {
    const fetcher = makeFetcher({});
    render(<FlowsteadApp client={new ApiClient({ fetcher })} />);
    expect(await screen.findByText('Alpha Plant')).toBeInTheDocument();
    expect(screen.getByTestId('sign-in-entry')).toBeInTheDocument();
    expect(screen.queryByTestId('sign-out')).not.toBeInTheDocument();
    expect(screen.queryByText(/Sign up|Create account|Register/i)).not.toBeInTheDocument();
  });

  it('valid invite/login shows the principal identity and private Plants only', async () => {
    const fetcher = makeFetcher({ 'principal-a': ['a'] });
    const auth = new TestAuthProvider({ token: 'TOKEN-principal-a', principalId: 'principal-a', expiresAt: Date.now() + 60_000 });
    render(<FlowsteadApp client={new ApiClient({ fetcher })} auth={auth} />);
    expect(await screen.findByTestId('session-identity')).toHaveTextContent('Operator · principal-a');
    expect(screen.getByTestId('sign-out')).toBeInTheDocument();
    expect(screen.queryByTestId('sign-in-entry')).not.toBeInTheDocument();
    expect(await screen.findByText('Plant a')).toBeInTheDocument();
    expect(screen.queryByText('Plant b')).not.toBeInTheDocument();
  });

  it('logout returns to public signed-out mode and clears identity', async () => {
    const fetcher = makeFetcher({ 'principal-a': ['a'] });
    const auth = new TestAuthProvider({ token: 'TOKEN-principal-a', principalId: 'principal-a', expiresAt: Date.now() + 60_000 });
    render(<FlowsteadApp client={new ApiClient({ fetcher })} auth={auth} />);
    await screen.findByTestId('session-identity');
    await userEvent.click(screen.getByTestId('sign-out'));
    await waitFor(() => expect(screen.queryByTestId('session-identity')).not.toBeInTheDocument());
    expect(screen.getByTestId('sign-in-entry')).toBeInTheDocument();
    expect(await screen.findByText('Alpha Plant')).toBeInTheDocument();
  });

  it('expired session (401) transitions to public with Session expired notice and clears private rows', async () => {
    const fetcher = vi.fn<typeof fetch>().mockImplementation(async (_input, init) => {
      const auth = new Headers(init?.headers).get('Authorization');
      if (auth) return new Response(JSON.stringify({ detail: { code: 'unauthorized' } }), { status: 401, headers: { 'Content-Type': 'application/json' } });
      return new Response(JSON.stringify({ plants: [plant('a', 'Alpha Plant')] }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
    const client = new ApiClient({ fetcher });
    const auth = new TestAuthProvider({ token: 'TOKEN-principal-a', principalId: 'principal-a', expiresAt: Date.now() + 60_000 });
    await preferences.saveForecast('a', forecastResponse('a') as never, 'principal-a');
    render(<FlowsteadApp client={client} auth={auth} />);
    expect(await screen.findByTestId('session-notice')).toHaveTextContent('Session expired');
    await waitFor(() => expect(screen.queryByTestId('session-identity')).not.toBeInTheDocument());
    expect(await screen.findByText('Alpha Plant')).toBeInTheDocument();
    expect(await preferences.loadForecast('a', 'principal-a')).toBeUndefined();
  });

  it('zero-Plant principal sees No plants assigned', async () => {
    const fetcher = makeFetcher({ 'principal-b': [] });
    const auth = new TestAuthProvider({ token: 'TOKEN-principal-b', principalId: 'principal-b', expiresAt: Date.now() + 60_000 });
    render(<FlowsteadApp client={new ApiClient({ fetcher })} auth={auth} />);
    expect(await screen.findByText('No plants assigned')).toBeInTheDocument();
  });
});

describe('SEC-M9-CACHE', () => {
  it('auth switch clears prior private rows from IndexedDB and memory and never renders stale Plants', async () => {
    const fetcher = makeFetcher({ 'principal-a': ['a'], 'principal-b': ['b'] });
    const client = new ApiClient({ fetcher });
    const auth = new TestAuthProvider({ token: 'TOKEN-principal-a', principalId: 'principal-a', expiresAt: Date.now() + 60_000 });
    render(<FlowsteadApp client={client} auth={auth} />);
    expect(await screen.findByText('Plant a')).toBeInTheDocument();
    await preferences.saveForecast('a', forecastResponse('a') as never, 'principal-a');
    expect(await preferences.loadForecast('a', 'principal-a')).toBeTruthy();

    // switch principal on the same mounted provider (account switch)
    auth.setSession({ token: 'TOKEN-principal-b', principalId: 'principal-b', expiresAt: Date.now() + 60_000 });
    expect(await screen.findByText('Plant b')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('Plant a')).not.toBeInTheDocument());
    // prior principal's private forecast snapshot cleared from IndexedDB and memory
    expect(await preferences.loadForecast('a', 'principal-a')).toBeUndefined();
  });

  it('never stores tokens or secret claims in IndexedDB rows', async () => {
    const fetcher = makeFetcher({ 'principal-a': ['a'] });
    const client = new ApiClient({ fetcher });
    const auth = new TestAuthProvider({ token: 'TOKEN-principal-a', principalId: 'principal-a', expiresAt: Date.now() + 60_000 });
    render(<FlowsteadApp client={client} auth={auth} />);
    await screen.findByTestId('session-identity');
    await userEvent.click(screen.getByTestId('sign-out'));
    await waitFor(() => expect(screen.getByTestId('sign-in-entry')).toBeInTheDocument());
    const rows = await new Promise<Array<Record<string, unknown>>>((resolve) => {
      const open = indexedDB.open('flowstead-preferences', 2);
      open.onsuccess = () => {
        const req = open.result.transaction('entries', 'readonly').objectStore('entries').getAll();
        req.onsuccess = () => { resolve(req.result as Array<Record<string, unknown>>); };
      };
    });
    expect(JSON.stringify(rows)).not.toContain('TOKEN-principal-a');
    expect(JSON.stringify(rows)).not.toContain('secret');
  });
});

describe('SIGN-IN FORM', () => {
  const openSignInModal = () => userEvent.click(screen.getByTestId('sign-in-entry'));

  it('successful sign-in passes credentials, closes the modal, and shows the private principal', async () => {
    const fetcher = anonymousFetcher();
    const auth = new TestAuthProvider(null, { email: 'op@example.com', password: 's3cret', principalId: 'principal-a' });
    render(<FlowsteadApp client={new ApiClient({ fetcher })} auth={auth} />);
    await screen.findByTestId('sign-in-entry');
    const signIn = vi.spyOn(auth, 'signIn');
    await openSignInModal();
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAccessibleName('Sign in');
    expect(screen.getByRole('textbox', { name: 'Email' })).toHaveFocus(); // Radix moves focus on open
    await userEvent.type(screen.getByLabelText('Email'), 'op@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 's3cret');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(signIn).toHaveBeenCalledWith('op@example.com', 's3cret');
    await waitFor(() => expect(screen.getByTestId('session-identity')).toHaveTextContent('principal-a'));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(await screen.findByText('Plant a')).toBeInTheDocument();
  });

  it('rejects bad credentials with an inline error and keeps the public signed-out view', async () => {
    const fetcher = anonymousFetcher();
    const auth = new TestAuthProvider(); // reject-all (fail closed)
    render(<FlowsteadApp client={new ApiClient({ fetcher })} auth={auth} />);
    await screen.findByTestId('sign-in-entry');
    await openSignInModal();
    await userEvent.type(screen.getByLabelText('Email'), 'op@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await waitFor(() => expect(screen.getByTestId('sign-in-error')).toBeInTheDocument());
    expect(screen.queryByTestId('session-identity')).not.toBeInTheDocument();
    // password input never leaks stored values into the DOM
    expect(screen.getByLabelText('Password')).toHaveValue('');
  });

  it('Escape closes the modal and password field is of type password with no signup links', async () => {
    const fetcher = anonymousFetcher();
    render(<FlowsteadApp client={new ApiClient({ fetcher })} auth={new TestAuthProvider()} />);
    await screen.findByTestId('sign-in-entry');
    await openSignInModal();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    // native `type=password` so the value is a secret input, never plaintext
    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password');
    expect(screen.queryByText(/Sign up|Create account|Register/i)).not.toBeInTheDocument();
    await userEvent.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });
});
