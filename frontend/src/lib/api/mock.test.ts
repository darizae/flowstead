import { describe, expect, it } from 'vitest';
import { mockApiClient } from './mock';

describe('bounded offline mock preview', () => {
  it('generates five fictional plants without a network connection', async () => {
    const { plants } = await mockApiClient.listPlants();
    expect(plants).toHaveLength(5);
    expect(new Set(plants.map((p) => p.plant_id)).size).toBe(5);
    expect(mockApiClient.hasPrincipal).toBe(false);
  });

  it('generates consistent latest, bounded history and twelve forecast points on demand', async () => {
    const latest = await mockApiClient.latestPlant('plant-01');
    const end = latest.reading.timestamp_utc;
    const start = new Date(Date.parse(end) - 168 * 3_600_000).toISOString();
    const history = await mockApiClient.historyPlant('plant-01', start, end);
    const forecast = await mockApiClient.forecastPlant('plant-01');
    expect(history.readings.length).toBeLessThanOrEqual(168);
    expect(history.readings.at(-1)?.measurements).toEqual(latest.reading.measurements);
    expect(forecast.forecasts).toHaveLength(12);
    expect(forecast.source_revision).toBe('mock-only');
    expect(await mockApiClient.historyPlant('plant-02', start, end)).not.toEqual(history);
  });

  it('does not provide private data or a pretend PDF report', async () => {
    await expect(mockApiClient.latestPlant('nonexistent')).rejects.toMatchObject({ code: 'plant_not_found' });
    await expect(mockApiClient.downloadReport()).rejects.toThrow('live API');
  });
});