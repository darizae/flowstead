import type { ForecastResponse } from '../../lib/api/types';
import { labelHistoryPoints, type LabeledHistoryPoint } from '../history/transforms';

export interface ForecastObservedPoint { timestampUtc: string; value: number }
export interface ForecastPoint extends ForecastObservedPoint { source: 'observed' | 'predicted' }

export const FORECAST_HOURS = 12;

/** Combine observed influent-flow points and the 12 predicted targets in time order. */
export function forecastPoints(forecast: ForecastResponse, observed: ForecastObservedPoint[]): ForecastPoint[] {
  const predicted: ForecastPoint[] = forecast.forecasts
    .filter((hour) => Number.isFinite(Date.parse(hour.target_time_utc)) && Number.isFinite(hour.predicted_flow_gal_h))
    .map((hour) => ({ timestampUtc: hour.target_time_utc, value: hour.predicted_flow_gal_h, source: 'predicted' }));
  const observedPoints: ForecastPoint[] = observed
    .filter((point) => Number.isFinite(Date.parse(point.timestampUtc)) && Number.isFinite(point.value))
    .map((point) => ({ ...point, source: 'observed' }));
  return [...observedPoints, ...predicted].sort((a, b) => Date.parse(a.timestampUtc) - Date.parse(b.timestampUtc));
}

export function labelForecastPoints(points: ForecastPoint[], plantTimeZone: string): LabeledHistoryPoint[] {
  return labelHistoryPoints(points.map((point) => ({ timestampUtc: point.timestampUtc, value: point.value, quality: 'valid' as const })), { timezone: plantTimeZone });
}

export function niceDomain(values: number[]): [number, number] {
  if (values.length === 0) return [0, 1];
  const low = Math.min(...values);
  const high = Math.max(...values);
  if (low === high) return [low - 1, high + 1];
  const pad = (high - low) * 0.08;
  return [low - pad, high + pad];
}

export function fullForecastLabel(forecast: ForecastResponse): string {
  if (forecast.status === 'unavailable') return 'Forecast unavailable';
  if (forecast.issued_at_utc && forecast.model_version) {
    return `Issued ${new Date(forecast.issued_at_utc).toISOString().slice(0, 16).replace('T', ' ')} UTC · ${forecast.model_version}`;
  }
  if (forecast.model_version) return `Model ${forecast.model_version}`;
  return 'Influent flow forecast';
}
