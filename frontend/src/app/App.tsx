import { downloadBlob } from '../lib/exports/download';
import { AppNavbar, AppNavbarLink, AppShell, Button, Card, Dialog, DialogContent, DialogDescription, DialogTitle, PageHeading, Spinner } from '@darizae/marisma';
import { lazy, Suspense, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { createApiClient, type ApiClient } from '../lib/api/client';
import { mockApiClient } from '../lib/api/mock';
import { ApiError, type HistoryReading, type LatestResponse, type PlantSummary } from '../lib/api/types';
import { preferences } from '../lib/cache/preferences';
import { PlantDetailHeader, PlantListRow, MetricCards } from '../features/plants/components';
import { MockPlantMap } from '../features/plants/MockPlantMap';
import { HistoryChart } from '../features/history/HistoryChart';
import { ForecastChart } from '../features/forecast/ForecastChart';
import { type ForecastObservedPoint } from '../features/forecast/transforms';
import { type ChannelKey, type HistoryRange } from '../features/history/transforms';
import { createDefaultAuthProvider, type AuthProvider, type AuthSession } from '../lib/auth/provider';
import '../app.css';
import { useForecastRequest, usePlantForecast, usePlantHistory, usePlantLatest, usePlants, usePreference } from './hooks';

function plantIdFromLocation(): string | undefined {
  const match = window.location.pathname.match(/^\/plants\/([^/]+)\/?$/);
  if (!match) return undefined;
  try { return decodeURIComponent(match[1]); } catch { return ''; }
}
function navigate(path: string): void { window.history.pushState({}, '', path); window.dispatchEvent(new PopStateEvent('popstate')); }

/** Recent valid observed influent-flow points for the observed→predicted boundary. */
function observedFromHistory(readings: HistoryReading[] | undefined): ForecastObservedPoint[] {
  if (!readings) return [];
  return readings
    .filter((reading) => reading.measurements.influent_flow.quality === 'valid' && reading.measurements.influent_flow.value !== null)
    .sort((a, b) => Date.parse(a.timestamp_utc) - Date.parse(b.timestamp_utc))
    .slice(-12)
    .map((reading) => ({ timestampUtc: reading.timestamp_utc, value: reading.measurements.influent_flow.value as number }));
}

export interface FlowsteadAppProps { client?: ApiClient; principalId?: string; auth?: AuthProvider }
const defaultApiClient = createApiClient();
const defaultAuthProvider = createDefaultAuthProvider();
const PlantMap = lazy(() => import('../features/plants/PlantMap').then((module) => ({ default: module.PlantMap })));

export default function FlowsteadApp({ client = defaultApiClient, principalId: principalIdProp, auth }: FlowsteadAppProps) {
  const provider = auth ?? defaultAuthProvider;
  const usingAuth = Boolean(auth);
  const [authSession, setAuthSession] = useState<AuthSession | null>(() => {
    const session = provider.getSession();
    if (session) client.setToken(session.token); else client.clearToken();
    return session;
  });
  const [notice, setNotice] = useState<string | null>(null);
  const [signInOpen, setSignInOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [signingIn, setSigningIn] = useState(false);
  const [signInError, setSignInError] = useState<string | null>(null);
  const [mockMode, setMockMode] = useState(false);

  const openSignIn = () => { setEmail(''); setPassword(''); setSignInError(null); setSigningIn(false); setSignInOpen(true); };
  const closeSignIn = () => { setPassword(''); setSignInError(null); setSigningIn(false); setSignInOpen(false); };
  const submitSignIn = async (event: FormEvent) => {
    event.preventDefault();
    if (!provider.signIn || !email || !password) return;
    setSigningIn(true); setSignInError(null);
    try {
      await provider.signIn(email, password);
      closeSignIn();
    } catch {
      // Provider error details can contain internal auth configuration data;
      // present a stable, non-enumerating failure to unauthenticated visitors.
      setPassword('');
      setSigningIn(false);
      setSignInError('Sign in failed. Check your credentials and try again.');
    }
  };

  const providerPrincipal = authSession?.principalId;
  const principalId = usingAuth ? providerPrincipal : (principalIdProp ?? providerPrincipal);
  const demoMode = mockMode && !principalId && import.meta.env.PROD;
  const activeClient = demoMode ? mockApiClient : client;
  const principalKey = demoMode ? 'mock:public' : (principalId ?? 'public');
  const [activePrincipalKey, setActivePrincipalKey] = useState(principalKey);
  const [selectedId, setSelectedId] = useState(plantIdFromLocation);
  const restoredPreference = useRef(false);
  const principalTransitioning = activePrincipalKey !== principalKey;
  const effectiveSelectedId = principalTransitioning ? undefined : selectedId;
  const { plants, loading, error, retry } = usePlants(activeClient, principalKey);
  const { preference, loading: preferenceLoading, save } = usePreference(principalId);
  const selectedPlant = useMemo(() => plants.find((plant) => plant.plant_id === effectiveSelectedId), [plants, effectiveSelectedId]);
  const detail = usePlantLatest(activeClient, selectedPlant?.plant_id, principalKey);

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
        // revoked plant 403/404: wipe private caches so no stale snapshot leaks.
        void preferences.clearPrivate();
      }
    });
    return () => client.setAuthFailureHandler(undefined);
  }, [client, provider]);

  useEffect(() => { const onPopState = () => setSelectedId(plantIdFromLocation()); window.addEventListener('popstate', onPopState); return () => window.removeEventListener('popstate', onPopState); }, []);
  useEffect(() => {
    if (!principalTransitioning) return;
    restoredPreference.current = false;
    setActivePrincipalKey(principalKey);
    setSelectedId(undefined);
    navigate('/plants');
  }, [principalKey, principalTransitioning]);
  useEffect(() => { restoredPreference.current = false; }, [principalId]);
  useEffect(() => {
    if (restoredPreference.current || principalTransitioning || loading || preferenceLoading) return;
    restoredPreference.current = true;
    if (!effectiveSelectedId && preference?.plantId && plants.some((plant) => plant.plant_id === preference.plantId)) {
      setSelectedId(preference.plantId); navigate(`/plants/${encodeURIComponent(preference.plantId)}`);
    }
  }, [effectiveSelectedId, loading, preferenceLoading, plants, preference, principalTransitioning]);
  const openPlant = (plant: PlantSummary) => { setSelectedId(plant.plant_id); if (!demoMode) save({ plantId: plant.plant_id }); navigate(`/plants/${encodeURIComponent(plant.plant_id)}`); };
  const goBack = () => { setSelectedId(undefined); navigate('/plants'); };
  const signOut = () => { setNotice(null); void provider.signOut(); };
  const topbar = <div className="top-meta"><span>Session identity</span>{principalId ? <span className="session-identity" data-testid="session-identity">Operator · {principalId}</span> : <Button type="button" variant="ghost" size="small" data-testid="sign-in-entry" onClick={openSignIn}>Sign in</Button>}{notice && <span className="session-notice" data-testid="session-notice" role="status">{notice}</span>}{principalId ? <Button type="button" variant="secondary" size="small" data-testid="sign-out" onClick={signOut}>Sign out</Button> : null}<span className="small-muted">Synthetic data · Florida</span></div>;
  return <><AppShell
    className="flowstead-marisma"
    data-testid="marisma-scope"
    data-marisma-accent="reedwater"
    data-marisma-mode="light"
    header={<AppNavbar className="topbar" sticky={false} navigationLabel="Main navigation"
      brand={<a className="brand" href="/plants" onClick={(event) => { event.preventDefault(); goBack(); }}><span className="mark" aria-hidden="true">≈</span><span>Flowstead</span></a>}
      actions={topbar}>
      <AppNavbarLink href="/plants" current onClick={(event) => { event.preventDefault(); goBack(); }}>Plants</AppNavbarLink>
    </AppNavbar>}
    mainId="main-content"
    mainClassName="shell"
    footer={<footer className="footer">Flowstead · bounded synthetic readings</footer>}
  >
    {import.meta.env.PROD && !principalId && <div className="demo-toolbar" role="group" aria-label="Sample data mode"><span>{demoMode ? 'MOCK PREVIEW · Invented readings, not live monitoring' : 'Sample app · Live data may be unavailable'}</span><Button type="button" size="small" variant="secondary" data-testid="mock-toggle" onClick={() => { setMockMode(!mockMode); setSelectedId(undefined); navigate('/plants'); }}>{demoMode ? 'Return to Live Data' : 'Load Mock Data'}</Button></div>}
    {principalTransitioning || preferenceLoading ? <LoadingState label="Loading Plants…" /> : effectiveSelectedId === undefined ? <Overview plants={plants} loading={loading} error={error} retry={retry} onSelect={openPlant} mock={demoMode} /> : <Detail client={activeClient} selectedId={effectiveSelectedId} selectedPlant={selectedPlant} plants={plants} loading={loading} listError={error} latest={detail.latest} detailLoading={detail.loading} detailError={detail.error} onBack={goBack} onSwitch={(id) => { const plant = plants.find((item) => item.plant_id === id); if (plant) openPlant(plant); }} retry={detail.retry} scopeKey={principalKey} />}
  </AppShell>
    <Dialog open={signInOpen} onOpenChange={(open) => { if (!open) closeSignIn(); }}>
      <DialogContent className="auth-modal-content" showCloseButton={false} aria-labelledby="sign-in-title" aria-describedby="sign-in-description">
        <DialogTitle id="sign-in-title">Sign in</DialogTitle>
        <DialogDescription id="sign-in-description">Sign in with your invited operator credentials. No account creation; contact your administrator for access.</DialogDescription>
        <form className="auth-form" onSubmit={submitSignIn} noValidate>
          <label htmlFor="sign-in-email">Email</label>
          <input id="sign-in-email" name="email" type="email" autoComplete="email" autoFocus={signInOpen} value={email} onChange={(event) => setEmail(event.target.value)} aria-label="Email" />
          <label htmlFor="sign-in-password">Password</label>
          <input id="sign-in-password" name="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} aria-label="Password" />
          {signInError && <p className="auth-error" role="alert" data-testid="sign-in-error">{signInError}</p>}
          <div className="auth-actions">
            <Button type="button" variant="secondary" size="small" onClick={closeSignIn}>Cancel</Button>
            <Button type="submit" variant="primary" size="small" loading={signingIn} disabled={signingIn || !email || !password}>Sign in</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  </>;
}

function LoadingState({ label }: { label: string }) {
  return <Card className="surface loading" role="status"><Spinner size="small" /><span>{label}</span></Card>;
}

function RetryButton({ children, onClick }: { children: string; onClick: () => void }) {
  return <Button type="button" variant="secondary" size="small" onClick={onClick}>{children}</Button>;
}


function Overview({ plants, loading, error, retry, onSelect, mock = false }: { plants: PlantSummary[]; loading: boolean; error?: ApiError; retry: () => void; onSelect: (plant: PlantSummary) => void; mock?: boolean }) {
  return <>
    <PageHeading className="page-head" eyebrow="Operations overview" title="Plants" description="Monitor the latest readings from authorized wastewater Plants." />
    {loading ? <LoadingState label="Loading Plants…" /> : error ? <div className="error-state" role="alert"><strong>{error.code === 'unauthorized' ? 'Session expired' : 'Plants unavailable'}</strong><p>{error.message}</p><RetryButton onClick={retry}>Retry</RetryButton></div> : plants.length === 0 ? <Card className="surface empty"><strong>No plants assigned</strong><span>There are no Plants available for this view.</span></Card> : <div className="overview-grid">
      <Card className="panel" aria-labelledby="plant-list-title">
        <div className="panel-head"><h2 id="plant-list-title">Plant list</h2><span className="small-muted">{plants.length} {plants.length === 1 ? 'Plant' : 'Plants'}</span></div>
        {plants.map((plant) => <PlantListRow key={plant.plant_id} plant={plant} onSelect={() => onSelect(plant)} />)}
      </Card>
      <Card className="panel map-panel" aria-labelledby="map-title">
        <div className="panel-head"><h2 id="map-title">Florida map</h2></div>
        <Suspense fallback={mock ? <MockPlantMap plants={plants} onSelect={onSelect} /> : <p className="small-muted">Preparing map…</p>}>
          <PlantMap plants={plants} onSelect={onSelect} fallback={mock ? <MockPlantMap plants={plants} onSelect={onSelect} /> : undefined} />
        </Suspense>
      </Card>
    </div>}
  </>;
}

function Detail({ client, selectedId: _selectedId, selectedPlant, plants, loading, listError, latest, detailLoading, detailError, onBack, onSwitch, retry, scopeKey }: { client: ApiClient; selectedId: string; selectedPlant?: PlantSummary; plants: PlantSummary[]; loading: boolean; listError?: ApiError; latest?: LatestResponse; detailLoading: boolean; detailError?: ApiError; onBack: () => void; onSwitch: (id: string) => void; retry: () => void; scopeKey: string }) {
  const [range, setRange] = useState<HistoryRange>(24);
  const [channel, setChannel] = useState<ChannelKey>('influent_flow');
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | undefined>();
  const scopeRef = useRef(scopeKey);
  const plantRef = useRef(selectedPlant?.plant_id);
  const mountedRef = useRef(true);
  const history = usePlantHistory(client, selectedPlant?.plant_id, range, scopeKey, latest?.reading.timestamp_utc);
  const forecast = usePlantForecast(client, selectedPlant?.plant_id, scopeKey);
  const observed = useMemo(() => observedFromHistory(history.history?.readings), [history.history]);
  const forecastRequest = useForecastRequest(client, selectedPlant?.plant_id, scopeKey, forecast.retry);
  scopeRef.current = scopeKey;
  plantRef.current = selectedPlant?.plant_id;
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);
  if (loading) return <LoadingState label="Loading Plant…" />;
  const download = () => {
    if (!selectedPlant || !latest || loading || listError || detailLoading || detailError || downloadLoading) return;
    const requestedScope = scopeKey;
    const requestedPlant = selectedPlant.plant_id;
    setDownloadLoading(true);
    setDownloadError(undefined);
    void client.downloadReport(requestedPlant).then(({ blob, fileName }) => {
      if (mountedRef.current && scopeRef.current === requestedScope && plantRef.current === requestedPlant) downloadBlob(blob, fileName);
    }).catch((error: unknown) => {
      if (mountedRef.current && scopeRef.current === requestedScope) setDownloadError(error instanceof ApiError ? error.message : 'Report download failed.');
    }).finally(() => { if (mountedRef.current && scopeRef.current === requestedScope) setDownloadLoading(false); });
  };
  if (listError?.code === 'unauthorized') return <div className="error-state" role="alert"><strong>Session expired</strong><p>Your authorized Plant list is no longer available.</p><RetryButton onClick={onBack}>All plants</RetryButton></div>;
  if (!selectedPlant) return <Card className="surface state"><strong>Plant not available</strong><p>This Plant is not available in your current view.</p><RetryButton onClick={onBack}>All plants</RetryButton></Card>;
  const reportDisabled = scopeKey === 'mock:public' || loading || Boolean(listError) || detailLoading || Boolean(detailError) || !latest;
  return (
    <>
      <PlantDetailHeader
        plant={selectedPlant}
        plants={plants}
        onBack={onBack}
        onSwitch={onSwitch}
        onDownload={download}
        downloadDisabled={reportDisabled}
        downloadLoading={downloadLoading}
      />
      {downloadError && <p className="error-state" role="alert">{downloadError}</p>}
      {detailLoading ? (
        <LoadingState label="Loading latest measurements…" />
      ) : detailError ? (
        <div className="error-state" role="alert">
          <strong>{detailError.code === 'plant_not_found' ? 'Plant not available' : detailError.code === 'unauthorized' ? 'Session expired' : 'Latest readings unavailable'}</strong>
          <p>{detailError.code === 'plant_not_found' ? 'This Plant is not available in your current view.' : detailError.message}</p>
          <RetryButton onClick={detailError.code === 'plant_not_found' ? onBack : retry}>{detailError.code === 'plant_not_found' ? 'All plants' : 'Retry'}</RetryButton>
        </div>
      ) : latest ? (
        <>
          <MetricCards measurements={latest.reading.measurements} />
          <div className="detail-grid">
            <Card className="history-panel" aria-labelledby="history-title">
              <h2 id="history-title">Measurement history</h2>
              {history.loading ? (
                <LoadingState label="Loading history…" />
              ) : history.error ? (
                <div className="error-state" role="alert"><strong>History unavailable</strong><p>{history.error.message}</p><RetryButton onClick={history.retry}>Retry</RetryButton></div>
              ) : history.history ? (
                <HistoryChart history={history.history} range={range} channel={channel} onRangeChange={setRange} onChannelChange={setChannel} />
              ) : (
                <p>No history is available for this Plant.</p>
              )}
            </Card>
            <Card className="forecast-panel" aria-labelledby="forecast-title">
              <div className="forecast-panel-head">
                <h2 id="forecast-title">Influent flow forecast</h2>
                {client.hasPrincipal ? (
                  <Button
                    type="button"
                    variant="secondary"
                    size="small"
                    data-testid="forecast-refresh"
                    disabled={forecastRequest.status === 'queued' || forecastRequest.status === 'processing'}
                    onClick={() => void forecastRequest.refresh()}
                  >
                    Refresh forecast
                  </Button>
                ) : null}
              </div>
              {forecastRequest.status ? (
                <p className={`forecast-request-status ${forecastRequest.status === 'failed' ? 'error' : ''}`} data-testid="forecast-request-status" role="status">
                  {forecastRequest.status === 'queued' ? 'Forecast queued' : forecastRequest.status === 'processing' ? 'Forecast processing' : forecastRequest.status === 'completed' ? 'Forecast completed' : forecastRequest.error?.message ?? 'Forecast refresh failed.'}
                </p>
              ) : null}
              {forecast.loading ? (
                <LoadingState label="Loading forecast…" />
              ) : forecast.error ? (
                <div className="error-state" role="alert"><strong>Forecast unavailable</strong><p>{forecast.error.message}</p><RetryButton onClick={forecast.retry}>Retry</RetryButton></div>
              ) : forecast.forecast ? (
                <ForecastChart forecast={forecast.forecast} observed={observed} />
              ) : (
                <p>No forecast is available for this Plant.</p>
              )}
            </Card>
          </div>
        </>
      ) : (
        <Card className="surface state"><strong>Latest readings unavailable</strong><p>Try again to load this Plant.</p><RetryButton onClick={retry}>Retry</RetryButton></Card>
      )}
    </>
  );
}
