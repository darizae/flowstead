import { AppNavbar, AppNavbarLink, AppShell, Button, Card, PageHeading, Spinner } from '@darizae/marisma';
import { useEffect, useMemo, useRef, useState } from 'react';
import { createApiClient, type ApiClient } from '../lib/api/client';
import { ApiError, type LatestResponse, type PlantSummary } from '../lib/api/types';
import { PlantDetailHeader, PlantListRow, MetricCards } from '../features/plants/components';
import { PlantMap } from '../features/plants/PlantMap';
import { HistoryChart } from '../features/history/HistoryChart';
import { type ChannelKey, type HistoryRange } from '../features/history/transforms';
import '../app.css';
import { usePlantHistory, usePlantLatest, usePlants, usePreference } from './hooks';

function plantIdFromLocation(): string | undefined {
  const match = window.location.pathname.match(/^\/plants\/([^/]+)\/?$/);
  if (!match) return undefined;
  try { return decodeURIComponent(match[1]); } catch { return ''; }
}
function navigate(path: string): void { window.history.pushState({}, '', path); window.dispatchEvent(new PopStateEvent('popstate')); }

export interface FlowsteadAppProps { client?: ApiClient; principalId?: string }
const defaultApiClient = createApiClient();

export default function FlowsteadApp({ client = defaultApiClient, principalId }: FlowsteadAppProps) {
  const principalKey = principalId ?? 'public';
  const [activePrincipalKey, setActivePrincipalKey] = useState(principalKey);
  const [selectedId, setSelectedId] = useState(plantIdFromLocation);
  const restoredPreference = useRef(false);
  const principalTransitioning = activePrincipalKey !== principalKey;
  const effectiveSelectedId = principalTransitioning ? undefined : selectedId;
  const { plants, loading, error, retry } = usePlants(client, principalKey);
  const { preference, loading: preferenceLoading, save } = usePreference(principalId);
  const selectedPlant = useMemo(() => plants.find((plant) => plant.plant_id === effectiveSelectedId), [plants, effectiveSelectedId]);
  const detail = usePlantLatest(client, selectedPlant?.plant_id, principalKey);
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
  const openPlant = (plant: PlantSummary) => { setSelectedId(plant.plant_id); save({ plantId: plant.plant_id }); navigate(`/plants/${encodeURIComponent(plant.plant_id)}`); };
  const goBack = () => { setSelectedId(undefined); navigate('/plants'); };
  return <AppShell
    className="flowstead-marisma"
    data-testid="marisma-scope"
    data-marisma-accent="reedwater"
    data-marisma-mode="light"
    header={<AppNavbar className="topbar" sticky={false} navigationLabel="Main navigation"
      brand={<a className="brand" href="/plants" onClick={(event) => { event.preventDefault(); goBack(); }}><span className="mark" aria-hidden="true">≈</span><span>Flowstead</span></a>}
      actions={<div className="top-meta">Synthetic data · Florida</div>}>
      <AppNavbarLink href="/plants" current onClick={(event) => { event.preventDefault(); goBack(); }}>Plants</AppNavbarLink>
    </AppNavbar>}
    mainId="main-content"
    mainClassName="shell"
    footer={<footer className="footer">Flowstead · bounded synthetic readings</footer>}
  >
    {principalTransitioning || preferenceLoading ? <LoadingState label="Loading Plants…" /> : effectiveSelectedId === undefined ? <Overview plants={plants} loading={loading} error={error} retry={retry} onSelect={openPlant} /> : <Detail client={client} selectedId={effectiveSelectedId} selectedPlant={selectedPlant} plants={plants} loading={loading} listError={error} latest={detail.latest} detailLoading={detail.loading} detailError={detail.error} onBack={goBack} onSwitch={(id) => { const plant = plants.find((item) => item.plant_id === id); if (plant) openPlant(plant); }} retry={detail.retry} scopeKey={principalKey} />}
  </AppShell>;
}

function LoadingState({ label }: { label: string }) {
  return <Card className="surface loading" role="status"><Spinner size="small" /><span>{label}</span></Card>;
}

function RetryButton({ children, onClick }: { children: string; onClick: () => void }) {
  return <Button type="button" variant="secondary" size="small" onClick={onClick}>{children}</Button>;
}


function Overview({ plants, loading, error, retry, onSelect }: { plants: PlantSummary[]; loading: boolean; error?: ApiError; retry: () => void; onSelect: (plant: PlantSummary) => void }) {
  return <>
    <PageHeading className="page-head" eyebrow="Operations overview" title="Plants" description="Monitor the latest readings from authorized wastewater Plants." />
    {loading ? <LoadingState label="Loading Plants…" /> : error ? <div className="error-state" role="alert"><strong>{error.code === 'unauthorized' ? 'Session expired' : 'Plants unavailable'}</strong><p>{error.message}</p><RetryButton onClick={retry}>Retry</RetryButton></div> : plants.length === 0 ? <Card className="surface empty"><strong>No plants assigned</strong><span>There are no Plants available for this view.</span></Card> : <div className="overview-grid">
      <Card className="panel" aria-labelledby="plant-list-title">
        <div className="panel-head"><h2 id="plant-list-title">Plant list</h2><span className="small-muted">{plants.length} {plants.length === 1 ? 'Plant' : 'Plants'}</span></div>
        {plants.map((plant) => <PlantListRow key={plant.plant_id} plant={plant} onSelect={() => onSelect(plant)} />)}
      </Card>
      <Card className="panel map-panel" aria-labelledby="map-title">
        <div className="panel-head"><h2 id="map-title">Florida map</h2></div>
        <PlantMap plants={plants} onSelect={onSelect} />
      </Card>
    </div>}
  </>;
}

function Detail({ client, selectedId: _selectedId, selectedPlant, plants, loading, listError, latest, detailLoading, detailError, onBack, onSwitch, retry, scopeKey }: { client: ApiClient; selectedId: string; selectedPlant?: PlantSummary; plants: PlantSummary[]; loading: boolean; listError?: ApiError; latest?: LatestResponse; detailLoading: boolean; detailError?: ApiError; onBack: () => void; onSwitch: (id: string) => void; retry: () => void; scopeKey: string }) {
  const [range, setRange] = useState<HistoryRange>(24);
  const [channel, setChannel] = useState<ChannelKey>('influent_flow');
  const history = usePlantHistory(client, selectedPlant?.plant_id, range, scopeKey, latest?.reading.timestamp_utc);
  if (loading) return <LoadingState label="Loading Plant…" />;
  if (listError?.code === 'unauthorized') return <div className="error-state" role="alert"><strong>Session expired</strong><p>Your authorized Plant list is no longer available.</p><RetryButton onClick={onBack}>All plants</RetryButton></div>;
  if (!selectedPlant) return <Card className="surface state"><strong>Plant not available</strong><p>This Plant is not available in your current view.</p><RetryButton onClick={onBack}>All plants</RetryButton></Card>;
  return <><PlantDetailHeader plant={selectedPlant} plants={plants} onBack={onBack} onSwitch={onSwitch} />{detailLoading ? <LoadingState label="Loading latest measurements…" /> : detailError ? <div className="error-state" role="alert"><strong>{detailError.code === 'plant_not_found' ? 'Plant not available' : detailError.code === 'unauthorized' ? 'Session expired' : 'Latest readings unavailable'}</strong><p>{detailError.code === 'plant_not_found' ? 'This Plant is not available in your current view.' : detailError.message}</p><RetryButton onClick={detailError.code === 'plant_not_found' ? onBack : retry}>{detailError.code === 'plant_not_found' ? 'All plants' : 'Retry'}</RetryButton></div> : latest ? <><MetricCards measurements={latest.reading.measurements} /><div className="detail-grid"><Card className="history-panel" aria-labelledby="history-title"><h2 id="history-title">Measurement history</h2>{history.loading ? <LoadingState label="Loading history…" /> : history.error ? <div className="error-state" role="alert"><strong>History unavailable</strong><p>{history.error.message}</p><RetryButton onClick={history.retry}>Retry</RetryButton></div> : history.history ? <HistoryChart history={history.history} range={range} channel={channel} onRangeChange={setRange} onChannelChange={setChannel} /> : <p>No history is available for this Plant.</p>}</Card><Card className="reserved"><h2>Influent flow forecast</h2><p>Forecast unavailable until the forecast API provides persisted results.</p></Card></div></> : <Card className="surface state"><strong>Latest readings unavailable</strong><p>Try again to load this Plant.</p><RetryButton onClick={retry}>Retry</RetryButton></Card>}</>;
}
