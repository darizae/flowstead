import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { PlantSummary } from '../../lib/api/types';
import { floridaPoint, FLORIDA_OUTLINE_PATH } from './floridaOutline';
import { MockPlantMap } from './MockPlantMap';

const tampa: PlantSummary = {
  plant_id: 'plant-01', name: 'Bayview Water Reclamation',
  location: { city: 'Tampa', state_code: 'FL', latitude: 27.9506, longitude: -82.4572 },
  timezone: 'America/New_York', links: { latest: '', history: '', forecast: '' },
};
const naples: PlantSummary = {
  ...tampa, plant_id: 'plant-05', name: 'Everglade Springs Facility',
  location: { ...tampa.location, city: 'Naples', latitude: 26.142, longitude: -81.7948 },
};

describe('offline geographic preview', () => {
  it('renders an actual Census-derived coastline with geographically projected, selectable markers', async () => {
    const onSelect = vi.fn();
    render(<MockPlantMap plants={[tampa, naples]} onSelect={onSelect} />);
    expect(screen.getByRole('region', { name: 'Geographic preview of mock Florida plants' })).toBeInTheDocument();
    expect(FLORIDA_OUTLINE_PATH.length).toBeGreaterThan(500);
    expect(screen.getByRole('button', { name: `Open ${tampa.name}` })).toHaveStyle(floridaPoint(tampa.location.longitude, tampa.location.latitude));
    expect(Number.parseFloat(floridaPoint(tampa.location.longitude, tampa.location.latitude).top)).toBeLessThan(
      Number.parseFloat(floridaPoint(naples.location.longitude, naples.location.latitude).top),
    );
    await userEvent.click(screen.getByRole('button', { name: `Open ${naples.name}` }));
    expect(onSelect).toHaveBeenCalledWith(naples);
  });
});