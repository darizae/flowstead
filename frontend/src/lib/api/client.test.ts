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

  it('UT-M7-FAIL calls the browser fetch function with its required global receiver', async () => {
    const originalFetch = globalThis.fetch;
    const fetcher = vi.fn(async function (this: unknown): Promise<Response> {
      if (this !== globalThis) throw new TypeError('Illegal invocation');
      return new Response(JSON.stringify({ plants: [] }), { status: 200 });
    });
    globalThis.fetch = fetcher as typeof fetch;
    try {
      await expect(new ApiClient().listPlants()).resolves.toEqual({ plants: [] });
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('UT-M7-FAIL maps 401 and non-leaking 404 responses', async () => {
    const unauthorized = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ detail: { code: 'unauthorized' } }), { status: 401 }));
    await expect(new ApiClient({ fetcher: unauthorized }).listPlants()).rejects.toMatchObject({ code: 'unauthorized', status: 401 });
    const missing = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ detail: { code: 'plant_not_found', message: 'Plant not found' } }), { status: 404 }));
    await expect(new ApiClient({ fetcher: missing }).latestPlant('not-a-real-id')).rejects.toMatchObject({ code: 'plant_not_found', status: 404 });
  });

  it('UT-M8-HISTORY requests the selected Plant-scoped half-open UTC window', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ plant: {}, from_utc: '', to_utc: '', readings: [] }), { status: 200 }));
    await new ApiClient({ basePath: '/api/v1', fetcher }).historyPlant('p1', '2025-01-01T00:00:00.000Z', '2025-01-02T00:00:00.000Z');
    expect(fetcher.mock.calls[0]?.[0]).toBe('/api/v1/public/plants/p1/history?from=2025-01-01T00%3A00%3A00.000Z&to=2025-01-02T00%3A00%3A00.000Z');
  });

  it('UT-M9-FORECAST requests the forecast endpoint (private when token set)', async () => {
    const fetcher = vi.fn<typeof fetch>().mockImplementation(async () => new Response(JSON.stringify({ status: 'available', plant: {}, forecasts: [] }), { status: 200 }));
    const client = new ApiClient({ basePath: '/api/v1', fetcher });
    await client.forecastPlant('p1');
    expect(fetcher.mock.calls[0]?.[0]).toBe('/api/v1/public/plants/p1/forecast');
    client.setToken('jwt');
    await client.forecastPlant('p1');
    expect(fetcher.mock.calls[1]?.[0]).toBe('/api/v1/plants/p1/forecast');
    const auth = new Headers(fetcher.mock.calls[1]?.[1]?.headers).get('Authorization');
    expect(auth).toBe('Bearer jwt');
  });

  it('UT-M11-PDF requests the current public/private report and returns a safe server filename', async () => {
    const pdf = new Uint8Array([37, 80, 68, 70, 45, 49]);
    const fetcher = vi.fn<typeof fetch>().mockImplementation(async () => new Response(pdf, {
      status: 200,
      headers: { 'Content-Type': 'application/pdf', 'Content-Disposition': 'attachment; filename="flowstead-demo-plant-plant-01.pdf"' },
    }));
    const client = new ApiClient({ basePath: '/api/v1', fetcher });
    const publicReport = await client.downloadReport('plant-01');
    expect(fetcher.mock.calls[0]?.[0]).toBe('/api/v1/public/plants/plant-01/report.pdf');
    expect(publicReport.fileName).toBe('flowstead-demo-plant-plant-01.pdf');
    const bytes = await new Promise<Uint8Array>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(new Uint8Array(reader.result as ArrayBuffer));
      reader.onerror = () => reject(reader.error);
      reader.readAsArrayBuffer(publicReport.blob);
    });
    expect(bytes).toEqual(pdf);
    client.setToken('jwt');
    await client.downloadReport('plant-01');
    expect(fetcher.mock.calls[1]?.[0]).toBe('/api/v1/plants/plant-01/report.pdf');
    expect(new Headers(fetcher.mock.calls[1]?.[1]?.headers).get('Authorization')).toBe('Bearer jwt');
  });
});
