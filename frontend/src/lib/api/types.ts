export type Quality = 'valid' | 'invalid' | 'missing';
export type MeasurementUnit = 'gal/h' | 'in/h' | 'mg/L' | 'unitless';

export interface PlantLocation { city: string; state_code: 'FL'; latitude: number; longitude: number }
export interface PlantLinks { latest: string; history: string; forecast: string }
export interface PlantSummary { plant_id: string; name: string; location: PlantLocation; timezone: string; links: PlantLinks }
export interface PlantListResponse { plants: PlantSummary[] }
export interface Measurement { value: number | null; quality: Quality; units: MeasurementUnit }
export interface Measurements {
  influent_flow: Measurement & { units: 'gal/h' };
  rainfall: Measurement & { units: 'in/h' };
  dissolved_oxygen: Measurement & { units: 'mg/L' };
  effluent_ph: Measurement & { units: 'unitless' };
}
export interface HistoryReading { plant_id: string; timestamp_utc: string; latest: false; measurements: Measurements }
export interface HistoryResponse { plant: PlantSummary; from_utc: string; to_utc: string; readings: HistoryReading[] }

export type ForecastStatus = 'available' | 'unavailable';
export interface ForecastHour {
  hour_number: number;
  target_time_utc: string;
  predicted_flow_gal_h: number;
  units: 'gal/h';
  source: string;
}
export interface ForecastResponse {
  plant: PlantSummary;
  status: ForecastStatus;
  issued_at_utc: string | null;
  model_version: string;
  source_revision: string | null;
  physical_bound_rule: string;
  forecasts: ForecastHour[];
  unavailable_reason: string | null;
}

export type ForecastJobStatus = 'queued' | 'processing' | 'completed' | 'failed';
export interface ForecastJobResponse {
  request_event_id: string;
  correlation_id: string;
  plant_id: string;
  status: ForecastJobStatus;
  requested_at_utc: string;
  completed_at_utc: string | null;
  diagnostic: string | null;
}

export type HistoryWindowHours = 24 | 72 | 168;
export interface LatestReading { plant_id: string; timestamp_utc: string; latest: true; measurements: Measurements }
export interface LatestResponse { latest: true; plant: PlantSummary; reading: LatestReading }

export type ApiErrorCode = 'unauthorized' | 'plant_not_found' | 'network' | 'http' | 'invalid_response';
export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status?: number;
  constructor(code: ApiErrorCode, message: string, status?: number) {
    super(message); this.name = 'ApiError'; this.code = code; this.status = status;
  }
}
export interface ErrorDetail { code?: string; message?: string }
