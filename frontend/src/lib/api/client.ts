import { ApiError, type ForecastJobResponse, type ForecastResponse, type HistoryResponse, type LatestResponse, type PlantListResponse, type ErrorDetail } from './types';

export interface ApiClientOptions { basePath?: string; fetcher?: typeof fetch; token?: string }

function normalizeBasePath(value: string): string { return `/${value.replace(/^\/+|\/+$/g, '')}`; }
const REQUEST_TIMEOUT_MS = 15_000;

export class ApiClient {
  private readonly basePath: string;
  private readonly fetcher: typeof fetch;
  private token?: string;
  private authFailureHandler?: (status: 401 | 403 | 404) => void;
  constructor(options: ApiClientOptions = {}) {
    this.basePath = normalizeBasePath(options.basePath ?? import.meta.env.VITE_API_BASE_PATH ?? '/api/v1');
    this.fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis);
    this.token = options.token;
  }
  setToken(token: string | undefined): void { this.token = token; }
  clearToken(): void { this.token = undefined; }
  setAuthFailureHandler(handler: ((status: 401 | 403 | 404) => void) | undefined): void { this.authFailureHandler = handler; }
  get hasPrincipal(): boolean { return Boolean(this.token); }
  private async get<T>(resource: string): Promise<T> {
    const headers = new Headers({ Accept: 'application/json' });
    if (this.token) headers.set('Authorization', `Bearer ${this.token}`);
    let response: Response;
    try { response = await this.fetcher(`${this.basePath}${resource}`, { headers, signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS) }); }
    catch { throw new ApiError('network', 'Unable to reach Flowstead. Check your connection and try again.'); }
    if (!response.ok) {
      let detail: ErrorDetail = {};
      try { const payload = await response.json() as { detail?: ErrorDetail }; detail = payload.detail ?? {}; } catch { /* non-json error */ }
      if (response.status === 401) {
        this.authFailureHandler?.(401);
        throw new ApiError('unauthorized', 'Your session is no longer authorized.', 401);
      }
      if (response.status === 403) {
        this.authFailureHandler?.(403);
        throw new ApiError('plant_not_found', 'Plant not available.', 403);
      }
      if (response.status === 404) {
        this.authFailureHandler?.(404);
        throw new ApiError('plant_not_found', 'Plant not available.', 404);
      }
      throw new ApiError('http', detail.message ?? 'Flowstead returned an error.', response.status);
    }
    try { return await response.json() as T; }
    catch { throw new ApiError('invalid_response', 'Flowstead returned an unreadable response.', response.status); }
  }
  private async post<T>(resource: string): Promise<T> {
    const headers = new Headers({ Accept: 'application/json' });
    if (this.token) headers.set('Authorization', `Bearer ${this.token}`);
    let response: Response;
    try { response = await this.fetcher(`${this.basePath}${resource}`, { method: 'POST', headers, signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS) }); }
    catch { throw new ApiError('network', 'Unable to reach Flowstead. Check your connection and try again.'); }
    if (!response.ok) {
      let detail: ErrorDetail = {};
      try { const payload = await response.json() as { detail?: ErrorDetail }; detail = payload.detail ?? {}; } catch { /* non-json error */ }
      if (response.status === 401) {
        this.authFailureHandler?.(401);
        throw new ApiError('unauthorized', 'Your session is no longer authorized.', 401);
      }
      if (response.status === 403 || response.status === 404) {
        this.authFailureHandler?.(response.status);
        throw new ApiError('plant_not_found', detail.message ?? 'Plant not available.', response.status);
      }
      throw new ApiError('http', detail.message ?? 'Flowstead returned an error.', response.status);
    }
    try { return await response.json() as T; }
    catch { throw new ApiError('invalid_response', 'Flowstead returned an unreadable response.', response.status); }
  }
  async downloadReport(plantId: string): Promise<{ blob: Blob; fileName: string }> {
    const headers = new Headers({ Accept: 'application/pdf' });
    if (this.token) headers.set('Authorization', `Bearer ${this.token}`);
    const path = `${this.basePath}${this.hasPrincipal ? '/plants' : '/public/plants'}/${encodeURIComponent(plantId)}/report.pdf`;
    let response: Response;
    try { response = await this.fetcher(path, { headers, signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS) }); }
    catch { throw new ApiError('network', 'Unable to reach Flowstead. Check your connection and try again.'); }
    if (!response.ok) {
      let detail: ErrorDetail = {};
      try { const payload = await response.json() as { detail?: ErrorDetail }; detail = payload.detail ?? {}; } catch { /* non-json error */ }
      if (response.status === 401) {
        this.authFailureHandler?.(401);
        throw new ApiError('unauthorized', 'Your session is no longer authorized.', 401);
      }
      if (response.status === 403 || response.status === 404) {
        this.authFailureHandler?.(response.status);
        throw new ApiError('plant_not_found', detail.message ?? 'Plant not available.', response.status);
      }
      throw new ApiError('http', detail.message ?? 'Flowstead returned an error.', response.status);
    }
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition') ?? '';
    const match = disposition.match(/filename=\"([A-Za-z0-9._-]+)\"/i);
    return { blob, fileName: match?.[1] ?? 'flowstead-plant-report.pdf' };
  }
  listPlants(): Promise<PlantListResponse> { return this.get<PlantListResponse>(this.hasPrincipal ? '/plants' : '/public/plants'); }
  latestPlant(plantId: string): Promise<LatestResponse> {
    return this.get<LatestResponse>(`${this.hasPrincipal ? '/plants' : '/public/plants'}/${encodeURIComponent(plantId)}/latest`);
  }
  historyPlant(plantId: string, from: string, to: string): Promise<HistoryResponse> {
    const params = new URLSearchParams({ from, to });
    return this.get<HistoryResponse>(`${this.hasPrincipal ? '/plants' : '/public/plants'}/${encodeURIComponent(plantId)}/history?${params.toString()}`);
  }
  forecastPlant(plantId: string): Promise<ForecastResponse> {
    return this.get<ForecastResponse>(`${this.hasPrincipal ? '/plants' : '/public/plants'}/${encodeURIComponent(plantId)}/forecast`);
  }
  requestForecast(plantId: string): Promise<ForecastJobResponse> {
    return this.post<ForecastJobResponse>(`/plants/${encodeURIComponent(plantId)}/forecast-requests`);
  }
  forecastRequest(correlationId: string): Promise<ForecastJobResponse> {
    return this.get<ForecastJobResponse>(`/forecast-requests/${encodeURIComponent(correlationId)}`);
  }
}

export function createApiClient(options?: ApiClientOptions): ApiClient { return new ApiClient(options); }
