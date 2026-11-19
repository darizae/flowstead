import type { ForecastResponse, HistoryResponse } from '../api/types';
import type { ChannelKey } from '../../features/history/transforms';
import { channelMeta } from '../../features/history/transforms';

export const MAX_HISTORY_EXPORT_ROWS = 168;
export const MAX_FORECAST_EXPORT_ROWS = 12;

export type CsvCell = string | number | null | undefined;

function formulaSafe(value: string): string {
  return /^[\u0000-\u0020\uFEFF]*[=+\-@]/.test(value) ? `'${value}` : value;
}

/** Quote every cell so commas, quotes, and CR/LF remain standards-compliant CSV. */
export function escapeCsvCell(value: CsvCell): string {
  if (value === null || value === undefined) return '""';
  if (typeof value === 'number' && !Number.isFinite(value)) throw new RangeError('CSV numeric values must be finite.');
  const text = typeof value === 'number' ? String(value) : formulaSafe(value);
  return `"${text.replaceAll('"', '""')}"`;
}

export function serializeCsv(headers: readonly string[], rows: readonly (readonly CsvCell[])[], maxRows = MAX_HISTORY_EXPORT_ROWS): string {
  if (headers.length === 0) throw new RangeError('CSV requires at least one header.');
  if (rows.length > maxRows) throw new RangeError(`CSV export is limited to ${maxRows} rows.`);
  for (const row of rows) {
    if (row.length !== headers.length) throw new RangeError('CSV row does not match the header width.');
  }
  return [headers, ...rows].map((row) => row.map(escapeCsvCell).join(',')).join('\r\n') + '\r\n';
}

function utc(value: string): string {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) throw new RangeError(`Invalid UTC timestamp: ${value}`);
  return date.toISOString();
}

export function serializeHistoryCsv(history: HistoryResponse, channel: ChannelKey): string {
  if (history.readings.length > MAX_HISTORY_EXPORT_ROWS) throw new RangeError(`History export is limited to ${MAX_HISTORY_EXPORT_ROWS} rows.`);
  const meta = channelMeta(channel);
  const rows = history.readings
    .slice()
    .sort((a, b) => Date.parse(a.timestamp_utc) - Date.parse(b.timestamp_utc))
    .map((reading) => {
      const measurement = reading.measurements[channel];
      return [
        history.plant.plant_id,
        history.plant.name,
        utc(reading.timestamp_utc),
        channel,
        measurement.units,
        measurement.value,
        measurement.quality,
      ] as const;
    });
  return serializeCsv(['plant_id', 'plant_name', 'timestamp_utc', 'measurement', 'unit', 'value', 'quality'], rows);
}

export function serializeForecastCsv(forecast: ForecastResponse): string {
  if (forecast.status !== 'available') throw new RangeError('Forecast is unavailable.');
  if (forecast.forecasts.length !== MAX_FORECAST_EXPORT_ROWS) throw new RangeError(`Forecast export requires exactly ${MAX_FORECAST_EXPORT_ROWS} targets.`);
  const issue = forecast.issued_at_utc === null ? null : utc(forecast.issued_at_utc);
  const rows = forecast.forecasts
    .slice()
    .sort((a, b) => a.hour_number - b.hour_number)
    .map((hour) => [
      forecast.plant.plant_id,
      forecast.plant.name,
      issue,
      utc(hour.target_time_utc),
      'influent_flow',
      hour.units,
      hour.predicted_flow_gal_h,
      'predicted',
      forecast.model_version,
    ] as const);
  return serializeCsv(
    ['plant_id', 'plant_name', 'issue_time_utc', 'target_time_utc', 'measurement', 'unit', 'value', 'quality', 'model_version'],
    rows,
    MAX_FORECAST_EXPORT_ROWS,
  );
}
