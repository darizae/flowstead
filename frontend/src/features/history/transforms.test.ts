import { describe, expect, it } from 'vitest';
import type { HistoryReading } from '../../lib/api/types';
import { historyWindow, plantHourLabel, qualitySegments } from './transforms';

const reading = (timestamp_utc: string, value: number | null, quality: 'valid' | 'missing' | 'invalid' = 'valid'): HistoryReading => ({
  plant_id: 'p1', timestamp_utc, latest: false, measurements: {
    influent_flow: { value, quality, units: 'gal/h' },
    rainfall: { value: 1, quality: 'valid', units: 'in/h' },
    dissolved_oxygen: { value: 2, quality: 'valid', units: 'mg/L' },
    effluent_ph: { value: 7, quality: 'valid', units: 'unitless' },
  },
});

describe('UT-M8-CHART history transforms', () => {
  it('keeps missing, invalid, and absent hours out of line segments', () => {
    const readings = [
      reading('2025-01-01T00:00:00Z', 1),
      reading('2025-01-01T01:00:00Z', null, 'missing'),
      reading('2025-01-01T02:00:00Z', 3, 'valid'),
      reading('2025-01-01T04:00:00Z', 5, 'valid'),
      reading('2025-01-01T05:00:00Z', 6, 'invalid'),
      reading('2025-01-01T06:00:00Z', 7, 'valid'),
    ];
    expect(qualitySegments(readings, 'influent_flow').map((segment) => segment.map((point) => point.value))).toEqual([[1], [3], [5], [7]]);
  });

  it('anchors the half-open window one hour after the canonical latest reading, not wall-clock now', () => {
    expect(historyWindow(24, '2025-01-01T00:00:00Z')).toEqual({ from: '2024-12-31T01:00:00.000Z', to: '2025-01-01T01:00:00.000Z' });
    expect(historyWindow(72, '2025-01-01T00:00:00Z').to).toBe('2025-01-01T01:00:00.000Z');
    expect(historyWindow(168, '2025-01-01T00:00:00Z').from).toBe('2024-12-25T01:00:00.000Z');
  });
});

describe('UT-M8-DST Plant-local labels', () => {
  it('labels both Eastern fall-back 01:00 hours with distinct offsets', () => {
    const early = plantHourLabel('2025-11-02T05:00:00Z', { timezone: 'America/New_York' });
    const late = plantHourLabel('2025-11-02T06:00:00Z', { timezone: 'America/New_York' });
    expect(early).toContain('01:00 EDT (UTC-04:00)');
    expect(late).toContain('01:00 EST (UTC-05:00)');
  });

  it('labels both Central fall-back 01:00 hours and does not invent spring-forward 02:00', () => {
    const early = plantHourLabel('2025-11-02T06:00:00Z', { timezone: 'America/Chicago' });
    const late = plantHourLabel('2025-11-02T07:00:00Z', { timezone: 'America/Chicago' });
    expect(early).toContain('01:00 CDT (UTC-05:00)');
    expect(late).toContain('01:00 CST (UTC-06:00)');
    expect(plantHourLabel('2025-03-09T07:00:00Z', { timezone: 'America/Chicago' })).toContain('01:00 CST');
    expect(plantHourLabel('2025-03-09T08:00:00Z', { timezone: 'America/Chicago' })).toContain('03:00 CDT');
  });
});
