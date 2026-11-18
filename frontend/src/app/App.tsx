import { useEffect, useMemo, useRef, useState } from 'react';
import { createApiClient, type ApiClient } from '../lib/api/client';
import { ApiError, type LatestResponse, type PlantSummary } from '../lib/api/types';
import { PlantDetailHeader, PlantListRow, MetricCards } from '../features/plants/components';
import '../app.css';
import { usePlantLatest, usePlants, usePreference } from './hooks';

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
  return <>
    <header className="topbar">
      <a className="brand" href="/plants" onClick={(event) => { event.preventDefault(); goBack(); }}><span className="mark" aria-hidden="true">≈</span><span>Flowstead</span></a>
      <nav className="topnav" aria-label="Main navigation"><a className="nav-link" aria-current="page" href="/plants" onClick={(event) => { event.preventDefault(); goBack(); }}>Plants</a></nav>
      <div className="top-meta">Synthetic data · Florida</div>
    </header>
    <main className="shell">
      {principalTransitioning || preferenceLoading ? <div className="surface loading" role="status">Loading Plants…</div> : effectiveSelectedId === undefined ? <Overview plants={plants} loading={loading} error={error} retry={retry} onSelect={openPlant} /> : <Detail selectedId={effectiveSelectedId} selectedPlant={selectedPlant} plants={plants} loading={loading} listError={error} latest={detail.latest} detailLoading={detail.loading} detailError={detail.error} onBack={goBack} onSwitch={(id) => { const plant = plants.find((item) => item.plant_id === id); if (plant) openPlant(plant); }} retry={detail.retry} />}
      <footer className="footer">Flowstead · bounded synthetic readings</footer>
    </main>
  </>;
}

function Overview({ plants, loading, error, retry, onSelect }: { plants: PlantSummary[]; loading: boolean; error?: ApiError; retry: () => void; onSelect: (plant: PlantSummary) => void }) {
  return <>
    <section className="page-head"><div><p className="eyebrow">Operations overview</p><h1>Plants</h1><p className="lede">Monitor the latest readings from authorized wastewater Plants.</p></div></section>
    {loading ? <div className="surface loading" role="status">Loading Plants…</div> : error ? <div className="error-state" role="alert"><strong>{error.code === 'unauthorized' ? 'Session expired' : 'Plants unavailable'}</strong><p>{error.message}</p><button className="retry" type="button" onClick={retry}>Retry</button></div> : plants.length === 0 ? <div className="surface empty"><strong>No plants assigned</strong><span>There are no Plants available for this view.</span></div> : <div className="overview-grid"><section className="surface panel" aria-labelledby="plant-list-title"><div className="panel-head"><h2 id="plant-list-title">Plant list</h2><span className="small-muted">{plants.length} {plants.length === 1 ? 'Plant' : 'Plants'}</span></div>{plants.map((plant) => <PlantListRow key={plant.plant_id} plant={plant} onSelect={() => onSelect(plant)} />)}</section><section className="surface panel" aria-labelledby="map-title"><div className="panel-head"><h2 id="map-title">Florida map</h2></div><div className="placeholder-map"><strong>Map placeholder · task-008</strong><p>Plant locations will appear here when the approved map integration is implemented. Select a Plant from the list.</p></div></section></div>}
  </>;
}

function Detail({ selectedId, selectedPlant, plants, loading, listError, latest, detailLoading, detailError, onBack, onSwitch, retry }: { selectedId: string; selectedPlant?: PlantSummary; plants: PlantSummary[]; loading: boolean; listError?: ApiError; latest?: LatestResponse; detailLoading: boolean; detailError?: ApiError; onBack: () => void; onSwitch: (id: string) => void; retry: () => void }) {
  if (loading) return <div className="surface loading" role="status">Loading Plant…</div>;
  if (listError?.code === 'unauthorized') return <div className="error-state" role="alert"><strong>Session expired</strong><p>Your authorized Plant list is no longer available.</p><button className="retry" type="button" onClick={onBack}>All plants</button></div>;
  if (!selectedPlant) return <section className="surface state"><strong>Plant not available</strong><p>This Plant is not available in your current view.</p><button className="retry" type="button" onClick={onBack}>All plants</button></section>;
  return <><PlantDetailHeader plant={selectedPlant} plants={plants} onBack={onBack} onSwitch={onSwitch} />{detailLoading ? <div className="surface loading" role="status">Loading latest measurements…</div> : detailError ? <div className="error-state" role="alert"><strong>{detailError.code === 'plant_not_found' ? 'Plant not available' : detailError.code === 'unauthorized' ? 'Session expired' : 'Latest readings unavailable'}</strong><p>{detailError.code === 'plant_not_found' ? 'This Plant is not available in your current view.' : detailError.message}</p><button className="retry" type="button" onClick={detailError.code === 'plant_not_found' ? onBack : retry}>{detailError.code === 'plant_not_found' ? 'All plants' : 'Retry'}</button></div> : latest ? <><MetricCards measurements={latest.reading.measurements} /><div className="reserved-grid"><section className="surface reserved"><h2>Measurement history</h2><p>History visualization is reserved for task-008. This view will use Plant-local time and preserve missing and invalid quality.</p></section><section className="surface reserved"><h2>Influent flow forecast</h2><p>Forecast visualization is reserved for task-009. No projected values are shown until the API provides them.</p></section></div></> : <div className="surface state"><strong>Latest readings unavailable</strong><p>Try again to load this Plant.</p><button className="retry" type="button" onClick={retry}>Retry</button></div>}</>;
}
