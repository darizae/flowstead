import type { ChannelKey, HistoryRange } from '../../features/history/transforms';
import type { PlantSummary } from '../api/types';

function safeFilePart(value: string): string {
  const part = value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  return part || 'plant';
}

export function historyCsvFileName(plant: Pick<PlantSummary, 'name' | 'plant_id'>, channel: ChannelKey, range: HistoryRange): string {
  return `flowstead-${safeFilePart(plant.name)}-${safeFilePart(plant.plant_id)}-${channel}-${range}h.csv`;
}

export function historyPngFileName(plant: Pick<PlantSummary, 'name' | 'plant_id'>, channel: ChannelKey, range: HistoryRange): string {
  return `flowstead-${safeFilePart(plant.name)}-${safeFilePart(plant.plant_id)}-${channel}-${range}h.png`;
}

export function forecastCsvFileName(plant: Pick<PlantSummary, 'name' | 'plant_id'>): string {
  return `flowstead-${safeFilePart(plant.name)}-${safeFilePart(plant.plant_id)}-forecast.csv`;
}

export function forecastPngFileName(plant: Pick<PlantSummary, 'name' | 'plant_id'>): string {
  return `flowstead-${safeFilePart(plant.name)}-${safeFilePart(plant.plant_id)}-forecast.png`;
}
