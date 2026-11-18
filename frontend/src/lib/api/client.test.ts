import { describe, expect, it, vi } from 'vitest';
import { ApiClient } from './client';

describe('ApiClient', () => {
  it('SEC-M7-CLIENT uses explicit API path and never sends a server key', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ plants: [] }), { status: 200 }));
    await new ApiClient({ basePath: '/api/v1', fetcher }).listPlants();
    expect(fetcher).toHaveBeenCalledWith('/api/v1/public/plants', expect.objectContaining({ headers: expect.any(Headers) }));
    const init = fetcher.mock.calls[0]?.[1];
    expect(new Headers(init?.headers).get('Authorization')).toBeNull();
    expect(JSON.stringify(import.meta.env)).not.toContain('SERVICE_ROLE');
  });

  it('UT-M7-FAIL maps 401 and non-leaking 404 responses', async () => {
    const unauthorized = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ detail: { code: 'unauthorized' } }), { status: 401 }));
    await expect(new ApiClient({ fetcher: unauthorized }).listPlants()).rejects.toMatchObject({ code: 'unauthorized', status: 401 });
    const missing = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ detail: { code: 'plant_not_found', message: 'Plant not found' } }), { status: 404 }));
    await expect(new ApiClient({ fetcher: missing }).latestPlant('not-a-real-id')).rejects.toMatchObject({ code: 'plant_not_found', status: 404 });
  });
});
