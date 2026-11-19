import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { ForecastResponse } from '../../lib/api/types';
import { ForecastChart, visibleForecastAxisTicks } from './ForecastChart';
import { forecastPoints } from './transforms';

const plant = (id = 'plant-01') => ({ plant_id: id, name: 'Alpha Plant', location: { city: 'Test City', state_code: 'FL' as const, latitude: 27, longitude: -81 }, timezone: 'America/New_York', links: { latest: '', history: '', forecast: '' } });

const availableForecast = (): ForecastResponse => ({
  plant: plant(),
  status: 'available',
  issued_at_utc: '2025-01-01T00:00:00.000Z',
  model_version: 'seasonal-naive-24h',
  source_revision: 'abc123',
  physical_bound_rule: 'non-negative',
  forecasts: Array.from({ length: 12 }, (_, index) => ({ hour_number: index + 1, target_time_utc: new Date(Date.UTC(2025, 0, 1, index + 1)).toISOString(), predicted_flow_gal_h: 100 + index, units: 'gal/h', source: 'seasonal_naive_24h' })),
  unavailable_reason: null,
});

describe('UT-M9-FORECAST', () => {
  it('renders exactly the 12 API forecast targets with issued and model labels', () => {
    const forecast = availableForecast();
    render(<ForecastChart forecast={forecast} observed={[]} />);
    const targets = screen.getAllByTestId('forecast-target');
    expect(targets).toHaveLength(12);
    expect(screen.getByText(/Issued 2025-01-01 00:00 UTC/)).toBeInTheDocument();
    expect(screen.getByText(/seasonal-naive-24h/)).toBeInTheDocument();
    expect(screen.getByText('Observed→predicted boundary')).toBeInTheDocument();
    expect(screen.getByText(/12 of 12 API targets/)).toBeInTheDocument();
    expect(screen.queryByTestId('forecast-unavailable')).not.toBeInTheDocument();
  });

  it('shows the observed-to-predicted boundary from history plus predicted points', () => {
    const forecast = availableForecast();
    const observed = Array.from({ length: 6 }, (_, index) => ({ timestampUtc: new Date(Date.UTC(2024, 11, 31, 18 + index)).toISOString(), value: 80 + index }));
    const points = forecastPoints(forecast, observed);
    expect(points.filter((point) => point.source === 'observed')).toHaveLength(6);
    expect(points.filter((point) => point.source === 'predicted')).toHaveLength(12);
    const { container } = render(<ForecastChart forecast={forecast} observed={observed} />);
    // observed line, predicted line, boundary divider, and 12 target points
    expect(container.querySelectorAll('polyline.chart-line')).toHaveLength(2);
    expect(container.querySelectorAll('line.chart-boundary')).toHaveLength(1);
    expect(container.querySelectorAll('circle.forecast-observed-point')).toHaveLength(6);
  });

  it('shows an explicit unavailable state and never invents predicted points', () => {
    const forecast: ForecastResponse = { plant: plant(), status: 'unavailable', issued_at_utc: null, model_version: 'seasonal-naive-24h', source_revision: null, physical_bound_rule: 'non-negative', forecasts: [], unavailable_reason: 'No persisted forecast yet' };
    render(<ForecastChart forecast={forecast} observed={[]} />);
    const unavailable = screen.getByTestId('forecast-unavailable');
    expect(within(unavailable).getByText('Forecast unavailable')).toBeInTheDocument();
    expect(within(unavailable).getByText(/No persisted forecast yet/)).toBeInTheDocument();
    expect(screen.queryAllByTestId('forecast-target')).toHaveLength(0);
  });

  it('shows an empty state when forecast lacks targets', () => {
    const forecast: ForecastResponse = { plant: plant(), status: 'available', issued_at_utc: '2025-01-01T00:00:00.000Z', model_version: 'm', source_revision: null, physical_bound_rule: 'non-negative', forecasts: [], unavailable_reason: null };
    render(<ForecastChart forecast={forecast} observed={[]} />);
    expect(screen.getByText('No forecast targets are available for this Plant.')).toBeInTheDocument();
    expect(screen.queryAllByTestId('forecast-target')).toHaveLength(0);
    expect(screen.getByText(/Targets are API-predicted values, never client-computed/)).toBeInTheDocument();
  });

});
describe('UT-M10-FORECAST-AXIS', () => {
  it('keeps first, middle, and last time labels on narrow chart sources', () => {
    const ticks = ['first', 'second', 'middle', 'fourth', 'last'];
    expect(visibleForecastAxisTicks(ticks, 390)).toEqual(['first', 'middle', 'last']);
    expect(visibleForecastAxisTicks(ticks, 760)).toEqual(ticks);
  });
});
