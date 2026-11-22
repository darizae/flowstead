import { ApiClient } from './client';
import { ApiError, type ForecastResponse, type HistoryReading, type HistoryResponse, type LatestResponse, type Measurements, type PlantListResponse, type PlantSummary } from './types';

// Deterministic, bounded, entirely browser-side demonstration. No network, tokens,
// persistent storage, or modification of the real backend is involved.
const SITES = [
  ['plant-01', 'Bayview Water Reclamation', 'Tampa', 27.9506, -82.4572],
  ['plant-02', 'Cypress Creek Treatment', 'Orlando', 28.5383, -81.3792],
  ['plant-03', 'Pelican Point Waterworks', 'Sarasota', 27.3364, -82.5307],
  ['plant-04', 'Mangrove Shores Plant', 'Fort Myers', 26.6406, -81.8723],
  ['plant-05', 'Everglade Springs Facility', 'Naples', 26.142, -81.7948],
] as const;

const plants: PlantSummary[] = SITES.map(([plant_id, name, city, latitude, longitude]) => ({
  plant_id, name, location: { city, state_code: 'FL', latitude, longitude },
  timezone: 'America/New_York',
  links: { latest: '', history: '', forecast: '' },
}));

const ANCHOR = Date.UTC(2025, 0, 1, 0);
const HOUR = 3_600_000;

function site(plantId: string): PlantSummary {
  const plant = plants.find((entry) => entry.plant_id === plantId);
  if (!plant) throw new ApiError('plant_not_found', 'Mock Plant not found.', 404);
  return plant;
}

function flow(index: number, hour: number): number {
  // Different daily phases, gentle weekly drift, and independent plant offsets.
  const daily = Math.sin(2 * Math.PI * (hour + index * 3) / 24);
  const weekly = Math.sin(2 * Math.PI * (hour + index * 11) / 168);
  return Math.round(1400 + 270 * index + 260 * daily + 85 * weekly);
}

function measurements(index: number, hour: number): Measurements {
  const rain = Math.max(0, Math.sin((hour + index * 19) * 0.19) - 0.68);
  return {
    influent_flow: { value: flow(index, hour), quality: 'valid', units: 'gal/h' },
    rainfall: { value: Math.round(rain * 100) / 100, quality: 'valid', units: 'in/h' },
    dissolved_oxygen: { value: Math.round((4.2 + index * 0.16 + 0.4 * Math.cos(hour / 9)) * 100) / 100, quality: 'valid', units: 'mg/L' },
    effluent_ph: { value: Math.round((7.1 + 0.14 * Math.sin(hour / 16 + index)) * 100) / 100, quality: 'valid', units: 'unitless' },
  };
}

export class MockApiClient extends ApiClient {
  override get hasPrincipal(): boolean { return false; }
  override async listPlants(): Promise<PlantListResponse> { return { plants }; }
  override async latestPlant(plantId: string): Promise<LatestResponse> {
    const plant = site(plantId);
    const index = plants.indexOf(plant);
    return { latest: true, plant, reading: { plant_id: plantId, timestamp_utc: new Date(ANCHOR).toISOString(), latest: true, measurements: measurements(index, 0) } };
  }
  override async historyPlant(plantId: string, from: string, to: string): Promise<HistoryResponse> {
    const plant = site(plantId);
    const index = plants.indexOf(plant);
    const start = Math.max(ANCHOR - 168 * HOUR, Date.parse(from));
    const end = Math.min(ANCHOR, Date.parse(to));
    if (!Number.isFinite(start) || !Number.isFinite(end)) throw new ApiError('invalid_response', 'Invalid history window.');
    const count = Math.max(0, Math.min(168, Math.floor((end - start) / HOUR) + 1));
    const readings: HistoryReading[] = Array.from({ length: count }, (_, i) => {
      const timestamp = end - (count - 1 - i) * HOUR;
      const hour = Math.round((timestamp - ANCHOR) / HOUR);
      return { plant_id: plantId, timestamp_utc: new Date(timestamp).toISOString(), latest: false, measurements: measurements(index, hour) };
    });
    return { plant, from_utc: from, to_utc: to, readings };
  }
  override async forecastPlant(plantId: string): Promise<ForecastResponse> {
    const plant = site(plantId);
    const index = plants.indexOf(plant);
    return {
      plant, status: 'available', issued_at_utc: new Date(ANCHOR).toISOString(),
      model_version: 'mock-seasonal-demo', source_revision: 'mock-only', physical_bound_rule: 'non-negative',
      forecasts: Array.from({ length: 12 }, (_, i) => ({
        hour_number: i + 1, target_time_utc: new Date(ANCHOR + (i + 1) * HOUR).toISOString(),
        predicted_flow_gal_h: flow(index, i + 1), units: 'gal/h' as const, source: 'mock-seasonal-demo',
      })), unavailable_reason: null,
    };
  }
  override async downloadReport(): Promise<{ blob: Blob; fileName: string }> {
    throw new ApiError('http', 'PDF reports require the live API. Mock data is for preview only.');
  }
}

export const mockApiClient = new MockApiClient();