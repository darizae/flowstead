import type { Measurement, Measurements, PlantSummary } from '../../lib/api/types';

export const METRIC_ORDER = [
  ['influent_flow', 'Influent flow', 'gal/h'],
  ['rainfall', 'Rainfall', 'in/h'],
  ['dissolved_oxygen', 'Dissolved oxygen', 'mg/L'],
  ['effluent_ph', 'Effluent pH', 'unitless'],
] as const satisfies ReadonlyArray<[keyof Measurements, string, string]>;

export function PlantListRow({ plant, onSelect }: { plant: PlantSummary; onSelect: () => void }) {
  return <button className="plant-row" type="button" onClick={onSelect}>
    <span><strong>{plant.name}</strong><small>{plant.location.city}, {plant.location.state_code}</small></span>
    <span aria-hidden="true" className="arrow">→</span>
  </button>;
}

export function PlantDetailHeader({ plant, plants, onBack, onSwitch }: { plant: PlantSummary; plants: PlantSummary[]; onBack: () => void; onSwitch: (plantId: string) => void }) {
  return <>
    <button className="back-link" type="button" onClick={onBack}>← <span>All plants</span></button>
    <div className="detail-header">
      <div><p className="eyebrow">Plant details</p><h1>{plant.name}</h1><p className="lede">{plant.location.city}, Florida · {plant.timezone}</p></div>
      <label className="switcher">Plant <select aria-label="Select plant" value={plant.plant_id} onChange={(event) => onSwitch(event.target.value)}>{plants.map((item) => <option key={item.plant_id} value={item.plant_id}>{item.name}</option>)}</select></label>
    </div>
  </>;
}

function measurementCopy(measurement: Measurement): { value: string; status: string } {
  if (measurement.quality === 'missing' || measurement.value === null) return { value: '—', status: 'Missing' };
  if (measurement.quality === 'invalid') return { value: '—', status: 'Invalid' };
  return { value: measurement.value.toLocaleString(undefined, { maximumFractionDigits: 2 }), status: 'Valid' };
}

export function MetricCards({ measurements }: { measurements: Measurements }) {
  return <div className="metrics" aria-label="Latest measurements">{METRIC_ORDER.map(([key, label, unit]) => {
    const copy = measurementCopy(measurements[key]);
    return <article className="metric-card surface" key={key}><p>{label}</p><strong>{copy.value} <small>{copy.value === '—' ? '' : unit}</small></strong><span>{copy.status}{copy.value === '—' ? ` · ${unit}` : ''}</span></article>;
  })}</div>;
}
