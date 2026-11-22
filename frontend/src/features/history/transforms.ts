import type { HistoryReading, MeasurementUnit, PlantSummary } from '../../lib/api/types';
import { parseUtcTimestamp } from '../../shared/domain/utc';

export const HISTORY_RANGES = [24, 72, 168] as const;
export type HistoryRange = (typeof HISTORY_RANGES)[number];

export const CHANNELS = [
  { key: 'influent_flow', label: 'Influent flow', unit: 'gal/h', axisLabel: 'Influent flow (gal/h)' },
  { key: 'rainfall', label: 'Rainfall', unit: 'in/h', axisLabel: 'Rainfall (in/h)' },
  { key: 'dissolved_oxygen', label: 'Dissolved oxygen', unit: 'mg/L', axisLabel: 'Dissolved oxygen (mg/L)' },
  { key: 'effluent_ph', label: 'Effluent pH', unit: 'unitless', axisLabel: 'Effluent pH' },
] as const satisfies ReadonlyArray<{ key: keyof HistoryReading['measurements']; label: string; unit: MeasurementUnit; axisLabel: string }>;

export type ChannelKey = (typeof CHANNELS)[number]['key'];
export type HistoryPoint = { timestampUtc: Date; value: number; quality: 'valid' };
export type HistorySegment = HistoryPoint[];
export type LabeledHistoryPoint = HistoryPoint & { label: string; timezoneAbbreviation: string; offset: string };

export function historyWindow(range: HistoryRange, latestTimestampUtc: string | Date): { from: string; to: string } {
  const latest = latestTimestampUtc instanceof Date ? latestTimestampUtc : parseUtcTimestamp(latestTimestampUtc, 'latest reading timestamp');
  const end = new Date(latest.getTime() + 60 * 60 * 1000);
  const start = new Date(end.getTime() - range * 60 * 60 * 1000);
  return { from: start.toISOString(), to: end.toISOString() };
}

export function channelMeta(key: ChannelKey) {
  return CHANNELS.find((channel) => channel.key === key) ?? CHANNELS[0];
}

function isValidValue(reading: HistoryReading, key: ChannelKey): boolean {
  const measurement = reading.measurements[key];
  return measurement.quality === 'valid' && measurement.value !== null && Number.isFinite(measurement.value);
}

/** Keep hourly gaps as separate paths; never bridge absent, missing, or invalid readings. */
export function qualitySegments(readings: HistoryReading[], key: ChannelKey): HistorySegment[] {
  const parsed = readings.map((reading) => ({ reading, timestamp: parseUtcTimestamp(reading.timestamp_utc, 'reading timestamp') }));
  const ordered = [...parsed].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  const segments: HistorySegment[] = [];
  let current: HistorySegment = [];
  let previousTime: number | undefined;
  for (const { reading, timestamp } of ordered) {
    const time = timestamp.getTime();
    const valid = isValidValue(reading, key);
    const contiguous = previousTime !== undefined && time - previousTime === 60 * 60 * 1000;
    if (!valid || (previousTime !== undefined && !contiguous)) {
      if (current.length > 0) segments.push(current);
      current = [];
    }
    if (valid) {
      const measurement = reading.measurements[key];
      current.push({ timestampUtc: timestamp, value: measurement.value as number, quality: 'valid' });
    }
    previousTime = time;
  }
  if (current.length > 0) segments.push(current);
  return segments;
}

function offsetFor(date: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone, timeZoneName: 'longOffset' }).formatToParts(date);
  const value = parts.find((part) => part.type === 'timeZoneName')?.value ?? 'GMT';
  return value === 'GMT' ? 'UTC+00:00' : value.replace('GMT', 'UTC');
}

function abbreviationFor(date: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone, timeZoneName: 'short' }).formatToParts(date);
  return parts.find((part) => part.type === 'timeZoneName')?.value ?? timeZone;
}

export function plantHourLabel(timestampUtc: Date, plant: Pick<PlantSummary, 'timezone'>): LabeledHistoryPoint['label'] {
  const formatted = new Intl.DateTimeFormat('en-US', {
    timeZone: plant.timezone,
    month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).format(timestampUtc);
  const abbreviation = abbreviationFor(timestampUtc, plant.timezone);
  const offset = offsetFor(timestampUtc, plant.timezone);
  return `${formatted} ${abbreviation} (${offset})`;
}

export function labelHistoryPoints(points: HistoryPoint[], plant: Pick<PlantSummary, 'timezone'>): LabeledHistoryPoint[] {
  return points.map((point) => ({
    ...point,
    label: plantHourLabel(point.timestampUtc, plant),
    timezoneAbbreviation: abbreviationFor(point.timestampUtc, plant.timezone),
    offset: offsetFor(point.timestampUtc, plant.timezone),
  }));
}

export function chartTicks(range: HistoryRange, fromUtc: string, toUtc: string): Date[] {
  const from = parseUtcTimestamp(fromUtc, 'window start').getTime();
  const to = parseUtcTimestamp(toUtc, 'window end').getTime();
  const count = 5;
  const step = (to - from) / (count - 1);
  return Array.from({ length: count }, (_, index) => new Date(from + step * index));
}
