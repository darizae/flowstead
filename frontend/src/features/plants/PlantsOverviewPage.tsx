import { Suspense, lazy } from 'react';
import { Card, PageHeading } from '@darizae/marisma';
import type { ApiError, PlantSummary } from '../../lib/api/types';
import { LoadingState, RetryButton } from '../../shared/components/Status';
import { PlantListRow } from './components';
import { MockPlantMap } from './MockPlantMap';

const PlantMap = lazy(() => import('./PlantMap').then((module) => ({ default: module.PlantMap })));

export interface PlantsOverviewPageProps {
  plants: PlantSummary[];
  loading: boolean;
  error?: ApiError;
  retry: () => void;
  onSelect: (plant: PlantSummary) => void;
  mock?: boolean;
}

export function PlantsOverviewPage({ plants, loading, error, retry, onSelect, mock = false }: PlantsOverviewPageProps) {
  return <>
    <PageHeading className="page-head" eyebrow="Operations overview" title="Plants" description="Monitor the latest readings from authorized wastewater Plants." />
    {loading ? <LoadingState label="Loading Plants…" /> : error ? <div className="error-state" role="alert"><strong>{error.code === 'unauthorized' ? 'Session expired' : 'Plants unavailable'}</strong><p>{error.message}</p><RetryButton onClick={retry}>Retry</RetryButton></div> : plants.length === 0 ? <Card className="surface empty"><strong>No plants assigned</strong><span>There are no Plants available for this view.</span></Card> : <div className="overview-grid">
      <Card className="panel" aria-labelledby="plant-list-title">
        <div className="panel-head"><h2 id="plant-list-title">Plant list</h2><span className="small-muted">{plants.length} {plants.length === 1 ? 'Plant' : 'Plants'}</span></div>
        {plants.map((plant) => <PlantListRow key={plant.plant_id} plant={plant} onSelect={() => onSelect(plant)} />)}
      </Card>
      <Card className="panel map-panel" aria-labelledby="map-title">
        <div className="panel-head"><h2 id="map-title">Florida map</h2></div>
        {mock ? <MockPlantMap plants={plants} onSelect={onSelect} /> : <Suspense fallback={<p className="small-muted">Preparing map…</p>}><PlantMap plants={plants} onSelect={onSelect} /></Suspense>}
      </Card>
    </div>}
  </>;
}