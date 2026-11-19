import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ApiClient } from '../lib/api/client';
import FlowsteadApp from './App';

const plant = (id: string, name: string) => ({ plant_id: id, name, location: { city: 'Test City', state_code: 'FL' as const, latitude: 27, longitude: -81 }, timezone: 'America/New_York', links: { latest: '', history: '', forecast: '' } });
const latest = (id: string) => ({ latest: true as const, plant: plant(id, 'Alpha Plant'), reading: { plant_id: id, timestamp_utc: '2025-01-01T00:00:00Z', latest: true as const, measurements: { influent_flow: { value: 10, quality: 'valid' as const, units: 'gal/h' as const }, rainfall: { value: null, quality: 'missing' as const, units: 'in/h' as const }, dissolved_oxygen: { value: 2, quality: 'invalid' as const, units: 'mg/L' as const }, effluent_ph: { value: 7, quality: 'valid' as const, units: 'unitless' as const } } } });

describe('Plants navigation', () => {
  it('UT-M7-NAV renders API Plants and supports detail/back without demo rows', async () => {
    window.history.replaceState({}, '', '/plants');
    const fetcher = vi.fn<typeof fetch>().mockImplementation(async (url) => new Response(JSON.stringify(String(url).endsWith('/latest') ? latest('a') : { plants: [plant('a', 'Alpha Plant')] }), { status: 200 }));
    render(<FlowsteadApp client={new ApiClient({ fetcher })} />);
    expect(await screen.findByText('Alpha Plant')).toBeInTheDocument();
    expect(screen.getByTestId('marisma-scope')).toHaveAttribute('data-marisma-accent', 'reedwater');
    expect(screen.getByTestId('marisma-scope')).toHaveAttribute('data-marisma-mode', 'light');
    expect(screen.getByRole('button', { name: /Alpha Plant/ })).toHaveClass('plant-row');
    expect(screen.getByRole('link', { name: 'Plants' })).toHaveAttribute('aria-current', 'page');
    await userEvent.click(screen.getByRole('button', { name: /Alpha Plant/ }));
    expect(await screen.findByRole('heading', { name: 'Measurement history' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /All plants/ }));
    expect(await screen.findByRole('heading', { name: 'Plant list' })).toBeInTheDocument();
  });

  it('UT-M7-FAIL handles empty and inaccessible direct links without leaking Plant data', async () => {
    window.history.replaceState({}, '', '/plants/foreign');
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ plants: [] }), { status: 200 }));
    render(<FlowsteadApp client={new ApiClient({ fetcher })} />);
    expect(await screen.findByText('Plant not available')).toBeInTheDocument();
    expect(screen.queryByText('foreign')).not.toBeInTheDocument();
  });

  it('UT-M7-FAIL offers retry for an API error', async () => {
    window.history.replaceState({}, '', '/plants');
    const fetcher = vi.fn<typeof fetch>().mockRejectedValue(new TypeError('offline'));
    render(<FlowsteadApp client={new ApiClient({ fetcher })} />);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument());
    expect(screen.getByRole('alert')).toHaveTextContent('Plants unavailable');
  });
});
