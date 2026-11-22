import {
  ApiError,
  type ForecastJobResponse,
  type ForecastResponse,
  type HistoryResponse,
  type LatestResponse,
  type PlantListResponse,
} from "./types";

/**
 * Targeted runtime validation of API responses at the transport boundary (#30).
 * The backend contract is trusted, but a single fetch layer should reject
 * structurally-unusable responses rather than let each consumer guess. Checks
 * are deliberately shallow: enough shape to guarantee the typed consumers
 * downstream never trip over missing arrays/objects or invalid enums.
 */

function invalid(message: string): never {
  throw new ApiError("invalid_response", message);
}

export function validatePlantList(value: unknown): PlantListResponse {
  if (
    typeof value !== "object" ||
    value === null ||
    !("plants" in value) ||
    !Array.isArray(value.plants)
  ) {
    invalid("Flowstead returned an unreadable Plant list.");
  }
  return value as PlantListResponse;
}

export function validateLatest(value: unknown): LatestResponse {
  if (typeof value !== "object" || value === null || !("reading" in value))
    invalid("Flowstead returned an unreadable latest-reading response.");
  const reading = value.reading;
  if (typeof reading !== "object" || reading === null)
    invalid("Flowstead returned an unreadable latest-reading response.");
  if (
    !("plant_id" in reading) ||
    typeof reading.plant_id !== "string" ||
    !("timestamp_utc" in reading) ||
    typeof reading.timestamp_utc !== "string"
  ) {
    invalid("Flowstead returned an unreadable latest-reading response.");
  }
  return value as LatestResponse;
}

export function validateHistory(value: unknown): HistoryResponse {
  if (
    typeof value !== "object" ||
    value === null ||
    !("readings" in value) ||
    !Array.isArray(value.readings)
  ) {
    invalid("Flowstead returned an unreadable history response.");
  }
  return value as HistoryResponse;
}

export function validateForecast(value: unknown): ForecastResponse {
  if (typeof value !== "object" || value === null)
    invalid("Flowstead returned an unreadable forecast response.");
  const status = "status" in value ? value.status : undefined;
  const forecasts = "forecasts" in value ? value.forecasts : undefined;
  if (
    (status !== "available" && status !== "unavailable") ||
    !Array.isArray(forecasts)
  ) {
    invalid("Flowstead returned an unreadable forecast response.");
  }
  return value as ForecastResponse;
}

export function validateForecastJob(value: unknown): ForecastJobResponse {
  if (typeof value !== "object" || value === null)
    invalid("Flowstead returned an unreadable forecast-request response.");
  const status = "status" in value ? value.status : undefined;
  const correlationId =
    "correlation_id" in value ? value.correlation_id : undefined;
  const validStatus =
    status === "queued" ||
    status === "processing" ||
    status === "completed" ||
    status === "failed";
  if (typeof correlationId !== "string" || !validStatus)
    invalid("Flowstead returned an unreadable forecast-request response.");
  return value as ForecastJobResponse;
}
