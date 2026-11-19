import { ApiError, type HistoryResponse, type LatestResponse, type PlantListResponse, type ErrorDetail } from './types';

export interface ApiClientOptions { basePath?: string; fetcher?: typeof fetch; token?: string }

function normalizeBasePath(value: string): string { return `/${value.replace(/^\/+|\/+$/g, '')}`; }

export class ApiClient {
  private readonly basePath: string;
  private readonly fetcher: typeof fetch;
  private token?: string;
  constructor(options: ApiClientOptions = {}) {
    this.basePath = normalizeBasePath(options.basePath ?? import.meta.env.VITE_API_BASE_PATH ?? '/api/v1');
    this.fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis);
    this.token = options.token;
  }
  setToken(token: string | undefined): void { this.token = token; }
  clearToken(): void { this.token = undefined; }
  get hasPrincipal(): boolean { return Boolean(this.token); }
  private async get<T>(resource: string): Promise<T> {
    const headers = new Headers({ Accept: 'application/json' });
    if (this.token) headers.set('Authorization', `Bearer ${this.token}`);
    let response: Response;
    try { response = await this.fetcher(`${this.basePath}${resource}`, { headers }); }
    catch { throw new ApiError('network', 'Unable to reach Flowstead. Check your connection and try again.'); }
    if (!response.ok) {
      let detail: ErrorDetail = {};
      try { const payload = await response.json() as { detail?: ErrorDetail }; detail = payload.detail ?? {}; } catch { /* non-json error */ }
      if (response.status === 401) throw new ApiError('unauthorized', 'Your session is no longer authorized.', 401);
      if (response.status === 404) throw new ApiError('plant_not_found', 'Plant not available.', 404);
      throw new ApiError('http', detail.message ?? `Flowstead returned ${response.status}.`, response.status);
    }
    try { return await response.json() as T; }
    catch { throw new ApiError('invalid_response', 'Flowstead returned an unreadable response.', response.status); }
  }
  listPlants(): Promise<PlantListResponse> { return this.get<PlantListResponse>(this.hasPrincipal ? '/plants' : '/public/plants'); }
  latestPlant(plantId: string): Promise<LatestResponse> {
    return this.get<LatestResponse>(`${this.hasPrincipal ? '/plants' : '/public/plants'}/${encodeURIComponent(plantId)}/latest`);
  }
  historyPlant(plantId: string, from: string, to: string): Promise<HistoryResponse> {
    const params = new URLSearchParams({ from, to });
    return this.get<HistoryResponse>(`${this.hasPrincipal ? '/plants' : '/public/plants'}/${encodeURIComponent(plantId)}/history?${params.toString()}`);
  }
}

export function createApiClient(options?: ApiClientOptions): ApiClient { return new ApiClient(options); }
