import type { ForecastResponse } from "../../lib/api/types";
import { parseUtcTimestamp, tryParseUtc } from "../../shared/domain/utc";
import {
  labelHistoryPoints,
  type LabeledHistoryPoint,
} from "../history/transforms";

export interface ForecastObservedPoint {
  timestampUtc: Date;
  value: number;
}
export interface ForecastPoint extends ForecastObservedPoint {
  source: "observed" | "predicted";
}

export const FORECAST_HOURS = 12;

/** Combine observed influent-flow points and the 12 predicted targets in time order. */
export function forecastPoints(
  forecast: ForecastResponse,
  observed: ForecastObservedPoint[],
): ForecastPoint[] {
  const predicted: ForecastPoint[] = forecast.forecasts.flatMap((hour) => {
    const timestamp = tryParseUtc(hour.target_time_utc);
    if (!timestamp || !Number.isFinite(hour.predicted_flow_gal_h)) return [];
    return [
      {
        timestampUtc: timestamp,
        value: hour.predicted_flow_gal_h,
        source: "predicted" as const,
      },
    ];
  });
  const observedPoints: ForecastPoint[] = observed
    .filter((point) => Number.isFinite(point.value))
    .map((point) => ({ ...point, source: "observed" }));
  return [...observedPoints, ...predicted].sort(
    (a, b) => a.timestampUtc.getTime() - b.timestampUtc.getTime(),
  );
}

export function labelForecastPoints(
  points: ForecastPoint[],
  plantTimeZone: string,
): LabeledHistoryPoint[] {
  return labelHistoryPoints(
    points.map((point) => ({
      timestampUtc: point.timestampUtc,
      value: point.value,
      quality: "valid" as const,
    })),
    { timezone: plantTimeZone },
  );
}

export function fullForecastLabel(forecast: ForecastResponse): string {
  if (forecast.status === "unavailable") return "Forecast unavailable";
  if (forecast.issued_at_utc && forecast.model_version) {
    const issued = parseUtcTimestamp(forecast.issued_at_utc, "issue time")
      .toISOString()
      .slice(0, 16)
      .replace("T", " ");
    return `Issued ${issued} UTC · ${forecast.model_version}`;
  }
  if (forecast.model_version) return `Model ${forecast.model_version}`;
  return "Influent flow forecast";
}
