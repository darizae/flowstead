import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

const evidenceDirectory = path.resolve(
  process.env.FLOWSTEAD_EVIDENCE_DIR ?? path.resolve(process.cwd(), '../docs/design/evidence'),
);
const channels = ['dissolved_oxygen', 'effluent_ph', 'influent_flow', 'rainfall'];
const cardLabels = ['Influent flow', 'Rainfall', 'Dissolved oxygen', 'Effluent pH'];
const cardUnits = ['gal/h', 'in/h', 'mg/L', 'unitless'];
const exec = promisify(execFile);

function safeFilePart(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}
function pngDimensions(bytes: Buffer): { width: number; height: number } {
  expect(bytes.subarray(0, 8).toString('hex')).toBe('89504e470d0a1a0a');
  expect(bytes.toString('ascii', 12, 16)).toBe('IHDR');
  return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
}

test.beforeEach(async ({ context }) => {
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
});

test.afterEach(async ({ context }, testInfo) => {
  const fileName = `${safeFilePart(testInfo.project.name)}-${safeFilePart(testInfo.title)}.zip`;
  await context.tracing.stop({ path: path.join(evidenceDirectory, fileName) });
});

test('IDB-M7-PREF UI-M7-PARITY E2E-M12-PATH public list, detail, back, deep-link and reload', async ({ page }, testInfo) => {
  testInfo.annotations.push({ type: 'coverage', description: 'IDB-M7-PREF real IndexedDB persistence, bounded maintenance, and reload restoration' });
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  await page.goto('/plants');
  const listResponse = await listResponsePromise;
  expect(listResponse.status()).toBe(200);
  const listPayload = await listResponse.json() as { plants: Array<{ plant_id: string; name: string }> };
  expect(listPayload.plants).toHaveLength(5);
  await expect(page.locator('.plant-row')).toHaveCount(listPayload.plants.length);
  for (const plant of listPayload.plants) {
    await expect(page.locator('.plant-row').filter({ hasText: plant.name })).toBeVisible();
  }
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth && document.body.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: path.join(evidenceDirectory, `plants-${testInfo.project.name}-overview.png`), fullPage: true });

  const firstPlant = listPayload.plants[0];
  await page.locator('.plant-row').first().focus();
  await expect(page.locator('.plant-row').first()).toBeFocused();
  await expect(page.locator(':focus-visible')).toBeVisible();
  await page.evaluate(() => new Promise<void>((resolve, reject) => {
    const open = indexedDB.open('flowstead-preferences');
    open.onerror = () => reject(open.error);
    open.onsuccess = () => {
      const database = open.result;
      const transaction = database.transaction('entries', 'readwrite');
      transaction.objectStore('entries').put({ schema: 2, namespace: 'principal:stale', kind: 'preference', key: '_pref', value: {}, savedAt: 1, expiresAt: 1, bytes: 2 }, '2:principal:stale:preference:_pref');
      transaction.oncomplete = () => { database.close(); resolve(); };
      transaction.onerror = () => reject(transaction.error);
    };
  }));
  const latestResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === `/api/v1/public/plants/${firstPlant.plant_id}/latest`);
  await page.keyboard.press('Enter');
  const latestResponse = await latestResponsePromise;
  expect(latestResponse.status()).toBe(200);
  const latestPayload = await latestResponse.json() as { plant: { plant_id: string }; reading: { measurements: Record<string, unknown> } };
  expect(latestPayload.plant.plant_id).toBe(firstPlant.plant_id);
  expect(Object.keys(latestPayload.reading.measurements).sort()).toEqual(channels);
  await expect(page).toHaveURL(`/plants/${encodeURIComponent(firstPlant.plant_id)}`);
  await expect(page.getByRole('heading', { name: firstPlant.name })).toBeVisible();
  await expect(page.locator('.metric-card')).toHaveCount(4);
  for (const [index, label] of cardLabels.entries()) {
    await expect(page.locator('.metric-card').nth(index)).toContainText(label);
    await expect(page.locator('.metric-card').nth(index)).toContainText(cardUnits[index]);
  }
  await expect.poll(async () => page.evaluate(() => new Promise<boolean>((resolve, reject) => {
    const open = indexedDB.open('flowstead-preferences');
    open.onerror = () => reject(open.error);
    open.onsuccess = () => {
      const request = open.result.transaction('entries', 'readonly').objectStore('entries').get('2:principal:stale:preference:_pref');
      request.onsuccess = () => { open.result.close(); resolve(request.result === undefined); };
      request.onerror = () => reject(request.error);
    };
  }))).toBeTruthy();
  await page.screenshot({ path: path.join(evidenceDirectory, `plants-${testInfo.project.name}-detail.png`), fullPage: true });

  await page.getByRole('button', { name: /All plants/ }).click();
  await expect(page).toHaveURL('/plants');
  await page.goto(`/plants/${encodeURIComponent(firstPlant.plant_id)}`);
  await expect(page.getByRole('heading', { name: firstPlant.name })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: firstPlant.name })).toBeVisible();
  await expect(page.locator('.metric-card')).toHaveCount(4);
  await page.goto('/plants');
  await expect(page).toHaveURL(`/plants/${encodeURIComponent(firstPlant.plant_id)}`);
  await expect(page.locator('.metric-card')).toHaveCount(4);
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth && document.body.scrollWidth <= window.innerWidth)).toBeTruthy();
});

test('UI-M8-MAP E2E-M12-MAP exact API marker/list identity, attribution, and live style response', async ({ page }) => {
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  const styleResponsePromise = page.waitForResponse((response) => response.url().includes('tiles.openfreemap.org/styles/liberty'));
  await page.goto('/plants');
  const listResponse = await listResponsePromise;
  expect(listResponse.status()).toBe(200);
  const payload = await listResponse.json() as { plants: Array<{ plant_id: string; name: string }> };
  await expect(page.locator('.plant-marker')).toHaveCount(payload.plants.length);
  const markerIds = await page.locator('.plant-marker').evaluateAll((markers) => markers.map((marker) => marker.getAttribute('data-plant-id')));
  expect(markerIds.sort()).toEqual(payload.plants.map((plant) => plant.plant_id).sort());
  await expect(page.locator('.plant-row')).toHaveCount(payload.plants.length);
  for (const plant of payload.plants) await expect(page.getByRole('button', { name: new RegExp(`Open ${plant.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`) })).toBeVisible();
  await expect(page.locator('.maplibregl-ctrl-attrib')).toContainText('OpenFreeMap');
  await expect(page.locator('.maplibregl-ctrl-attrib')).toContainText('OpenStreetMap');
  expect((await styleResponsePromise).status()).toBe(200);
});

test('UI-M8-MAP keyboard marker activation opens its API Plant', async ({ page }) => {
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  await page.goto('/plants');
  const payload = await (await listResponsePromise).json() as { plants: Array<{ plant_id: string; name: string }> };
  const first = payload.plants[0];
  const latestResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === `/api/v1/public/plants/${encodeURIComponent(first.plant_id)}/latest`);
  const marker = page.locator(`.plant-marker[data-plant-id="${first.plant_id}"]`);
  await marker.focus();
  await expect(marker).toBeFocused();
  await page.keyboard.press('Enter');
  expect((await latestResponsePromise).status()).toBe(200);
  await expect(page.getByRole('heading', { name: first.name })).toBeVisible();
});

test('UI-M8-MAP E2E-M12-MAP deterministic style failure keeps API list fallback usable', async ({ page }) => {
  await page.route('**/styles/liberty*', (route) => route.abort());
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  await page.goto('/plants');
  const payload = await (await listResponsePromise).json() as { plants: Array<{ plant_id: string }> };
  await expect(page.locator('.plant-row')).toHaveCount(payload.plants.length);
  await expect(page.getByTestId('map-fallback')).toContainText('Map unavailable');
  await expect(page.locator('.plant-marker')).toHaveCount(0);
});

test('UI-M8-MAP E2E-M12-MAP deterministic WebGL failure keeps API list fallback usable', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', { configurable: true, value: () => null });
  });
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  await page.goto('/plants');
  const payload = await (await listResponsePromise).json() as { plants: Array<{ plant_id: string }> };
  await expect(page.locator('.plant-row')).toHaveCount(payload.plants.length);
  await expect(page.getByTestId('map-fallback')).toContainText('Map unavailable');
  await expect(page.locator('.plant-marker')).toHaveCount(0);
});

test('UI-M12-ALL E2E-M12-PATH API outage has a useful retry and recovers without stale data', async ({ page }) => {
  await page.route('**/api/v1/public/plants', (route) => route.abort('failed'));
  await page.goto('/plants');
  await expect(page.getByRole('alert')).toContainText('Plants unavailable');
  await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();
  await page.unroute('**/api/v1/public/plants');
  const recoveredResponse = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  await page.getByRole('button', { name: 'Retry' }).click();
  expect((await recoveredResponse).status()).toBe(200);
  await expect(page.locator('.plant-row')).toHaveCount(5);
});

test('UI-M8-PARITY UI-M12-ALL desktop and mobile expose four chart channels, units, 24-72-168 controls, keyboard focus, and 200% scale', async ({ page }, testInfo) => {
  const viewport = page.viewportSize();
  expect(viewport).toEqual(expect.objectContaining(testInfo.project.name === 'mobile' ? { width: 390, height: 844 } : { width: 1330, height: 900 }));
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  await page.goto('/plants');
  const payload = await (await listResponsePromise).json() as { plants: Array<{ plant_id: string; name: string }> };
  const first = payload.plants[0];
  const latestResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === `/api/v1/public/plants/${encodeURIComponent(first.plant_id)}/latest`);
  const historyResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === `/api/v1/public/plants/${encodeURIComponent(first.plant_id)}/history`);
  await page.locator('.plant-row').first().click();
  const latestResponse = await latestResponsePromise;
  const latestPayload = await latestResponse.json() as { reading: { timestamp_utc: string } };
  const historyResponse = await historyResponsePromise;
  expect(historyResponse.status()).toBe(200);
  const historyUrl = new URL(historyResponse.url());
  const anchor = new Date(new Date(latestPayload.reading.timestamp_utc).getTime() + 60 * 60 * 1000);
  expect(historyUrl.searchParams.get('to')).toBe(anchor.toISOString());
  expect(historyUrl.searchParams.get('from')).toBe(new Date(anchor.getTime() - 24 * 60 * 60 * 1000).toISOString());
  await expect(page.getByTestId('history-chart')).toBeVisible();
  for (const [label, axisLabel] of [
    ['Influent flow', 'Influent flow (gal/h)'],
    ['Rainfall', 'Rainfall (in/h)'],
    ['Dissolved oxygen', 'Dissolved oxygen (mg/L)'],
    ['Effluent pH', 'Effluent pH'],
  ]) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await expect(page.locator('[data-testid="history-chart"] h3')).toHaveText(axisLabel);
  }
  const rangeSelect = page.getByRole('combobox', { name: 'History range' });
  for (const range of [72, 168, 24]) {
    const nextHistory = page.waitForResponse((response) => new URL(response.url()).pathname === `/api/v1/public/plants/${encodeURIComponent(first.plant_id)}/history`);
    await rangeSelect.click();
    await page.getByRole('option', { name: range === 168 ? '7 days' : `${range} hours`, exact: true }).click();
    const response = await nextHistory;
    expect(new URL(response.url()).searchParams.get('to')).toBe(anchor.toISOString());
    expect(new URL(response.url()).searchParams.get('from')).toBe(new Date(anchor.getTime() - range * 60 * 60 * 1000).toISOString());
  }
  await expect(rangeSelect).toContainText('24 hours');
  const session = await page.context().newCDPSession(page);
  await session.send('Emulation.setPageScaleFactor', { pageScaleFactor: 2 });
  await page.getByRole('button', { name: 'Influent flow', exact: true }).focus();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Rainfall', exact: true })).toBeFocused();
  await expect(page.locator(':focus-visible')).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth && document.body.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
  await page.screenshot({ path: path.join(evidenceDirectory, `t012-${testInfo.project.name}-200-percent.png`), fullPage: true });
  await session.send('Emulation.setPageScaleFactor', { pageScaleFactor: 1 });
});

/**
 * T-009 browser auth is a deterministic test-only seam injected before app load.
 * The real local FastAPI verifies the injected RS256 JWT against the harness's
 * local mock Supabase Auth authority (see run_local.py), so private Plant,
 * forecast and forecast-command reads are truly authorized/denied by the API.
 */
function installTestAuth(page: Page, arg: { token?: string; principalId?: string }): Promise<void> {
  return page.addInitScript(({ token, principalId }) => {
    const signedOutKey = 'flowstead_test_signed_out';
    // A sign-out must survive a reload: the init script re-runs on every
    // navigation, so remember an explicit sign-out in sessionStorage and start
    // signed out if it is present.
    let startSignedOut = false;
    try { startSignedOut = sessionStorage.getItem(signedOutKey) === '1'; } catch { /* about:blank */ }
    function makeAuth() {
      let session = startSignedOut || !token ? null : { token, principalId, expiresAt: Date.now() + 10 * 60 * 1000 };
      const listeners = new Set<() => void>();
      return {
        getSession: () => session,
        signOut: async () => { session = null; try { sessionStorage.setItem(signedOutKey, '1'); } catch { /* ignore */ } listeners.forEach((listener) => listener()); },
        subscribe: (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; },
      };
    }
    (window as unknown as Record<string, unknown>).__FLOWSTEAD_TEST_AUTH__ = makeAuth();
  }, arg);
}

test('E2E-M12-PATH E2E-M12-INDEX private queue journey preserves authorization, cache clearing, and a clean browser console', async ({ page }, testInfo) => {
  const tokenA = process.env.FLOWSTEAD_TEST_PRINCIPAL_A_TOKEN;
  const tokenB = process.env.FLOWSTEAD_TEST_PRINCIPAL_B_TOKEN;
  expect(tokenA).toBeTruthy();
  expect(tokenB).toBeTruthy();
  const browserErrors: string[] = [];
  page.on('pageerror', (error) => browserErrors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error') browserErrors.push(message.text()); });
  await installTestAuth(page, { token: tokenA, principalId: 'test-principal-a' });
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/plants');
  await page.goto('/plants');
  const listResponse = await listResponsePromise;
  expect(listResponse.status()).toBe(200);
  const body = await listResponse.json() as { plants: Array<{ plant_id: string }> };
  expect(body.plants.map((plant) => plant.plant_id).sort()).toEqual(['plant-01', 'plant-02']);
  await page.locator('.plant-row').first().click();
  await expect(page.getByTestId('history-chart')).toBeVisible();
  await expect(page.getByTestId('forecast-target')).toHaveCount(12);

  const csvDownloadPromise = page.waitForEvent('download');
  await page.getByTestId('history-export-footer').getByRole('button', { name: 'Download CSV' }).click();
  const csvPath = await (await csvDownloadPromise).path();
  expect(csvPath).toBeTruthy();
  if (!csvPath) throw new Error('History CSV download path missing');
  expect((await readFile(csvPath, 'utf8')).split('\r\n')[0]).toContain('"plant_id"');

  const queueResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === '/api/v1/plants/plant-01/forecast-requests'
  ));
  await page.getByTestId('forecast-refresh').click();
  const queueResponse = await queueResponsePromise;
  expect(queueResponse.status()).toBe(202);
  expect((await queueResponse.json() as { status: string }).status).toBe('queued');
  await expect(page.getByTestId('forecast-request-status')).toHaveText('Forecast queued');
  await expect(page.getByTestId('forecast-request-status')).toHaveText('Forecast completed', { timeout: 15_000 });
  await expect(page.getByTestId('forecast-target')).toHaveCount(12);
  expect(browserErrors).toEqual([]);
  await page.screenshot({ path: path.join(evidenceDirectory, `t012-${testInfo.project.name}-private-detail.png`), fullPage: true });

  const deniedStatuses = await page.evaluate(async ({ bearerA, bearerB }) => {
    const [foreign, anonymous] = await Promise.all([
      fetch('/api/v1/plants/plant-01/latest', { headers: { Authorization: `Bearer ${bearerB}` } }),
      fetch('/api/v1/plants', { headers: { Accept: 'application/json' } }),
    ]);
    const own = await fetch('/api/v1/plants/plant-01/latest', { headers: { Authorization: `Bearer ${bearerA}` } });
    return { foreign: foreign.status, anonymous: anonymous.status, own: own.status };
  }, { bearerA: tokenA, bearerB: tokenB });
  expect(deniedStatuses).toEqual({ foreign: 404, anonymous: 401, own: 200 });

  await page.getByTestId('sign-out').click();
  await expect(page.getByTestId('sign-in-entry')).toBeVisible();
  await expect.poll(async () => page.evaluate(() => {
    const { promise, resolve, reject } = Promise.withResolvers<number>();
    const open = indexedDB.open('flowstead-preferences');
    open.onerror = () => reject(open.error);
    open.onsuccess = () => {
      const request = open.result.transaction('entries', 'readonly').objectStore('entries').openCursor();
      let count = 0;
      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const cursor = request.result;
        if (!cursor) { open.result.close(); resolve(count); return; }
        if (String(cursor.key).includes('principal:')) count += 1;
        cursor.continue();
      };
    };
    return promise;
  })).toBe(0);
  await page.screenshot({ path: path.join(evidenceDirectory, `t012-${testInfo.project.name}-integrated-path.png`), fullPage: true });
});

test('UT-M9-FORECAST UI-M9-PARITY real API shows 12 forecast targets and an observed→predicted boundary', async ({ page }, testInfo) => {
  testInfo.annotations.push({ type: 'coverage', description: 'UT-M9-FORECAST: exactly 12 API forecast targets, issued/model label, boundary, gal/h, local time' });
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  await page.goto('/plants');
  const payload = await (await listResponsePromise).json() as { plants: Array<{ plant_id: string; name: string }> };
  const first = payload.plants[0];
  const forecastResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === `/api/v1/public/plants/${encodeURIComponent(first.plant_id)}/forecast`);
  await page.locator('.plant-row').first().click();
  const forecastResponse = await forecastResponsePromise;
  expect(forecastResponse.status()).toBe(200);
  const body = await forecastResponse.json() as { status: string; forecasts: unknown[] };
  expect(body.status).toBe('available');
  expect(body.forecasts).toHaveLength(12);
  await expect(page.getByTestId('forecast-chart')).toBeVisible();
  await expect(page.getByTestId('forecast-target')).toHaveCount(12);
  await expect(page.locator('[data-testid="forecast-chart"] .chart-boundary')).toHaveCount(1);
  await expect(page.getByTestId('forecast-issue')).toContainText('seasonal_naive_24h');
  await expect(page.getByTestId('forecast-chart')).toContainText('Influent flow (gal/h)');
  await expect(page.getByTestId('forecast-chart')).toContainText('Observed→predicted boundary');
  await page.screenshot({ path: path.join(evidenceDirectory, `plants-${testInfo.project.name}-forecast.png`), fullPage: true });
});
test('UI-M10-PNG UI-M10-PARITY E2E-M12-FILES actual CSV parsing, PNG decoding, and bounded private actions', async ({ page }, testInfo) => {
  testInfo.annotations.push({ type: 'coverage', description: 'UI-M10-CSV/PNG: parse history and forecast downloads; decode PNG IHDR dimensions; verify chart axes, units, timezone and evidence screenshot' });
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  await page.goto('/plants');
  const payload = await (await listResponsePromise).json() as { plants: Array<{ plant_id: string }> };
  const first = payload.plants[0];
  if (!first) throw new Error('Public Plant fixture missing');
  await page.locator('.plant-row').first().click();
  await expect(page.getByTestId('history-chart')).toBeVisible();
  await expect(page.getByTestId('history-chart')).toContainText('Plant-local time');
  await expect(page.getByTestId('history-chart')).toContainText('UTC');
  await expect(page.getByTestId('history-chart')).toContainText('gal/h');
  const historyFooter = page.getByTestId('history-export-footer');
  const historyCsvDownload = page.waitForEvent('download');
  await historyFooter.getByRole('button', { name: 'Download CSV' }).click();
  const historyCsv = await historyCsvDownload;
  const historyCsvPath = await historyCsv.path();
  expect(historyCsvPath).toBeTruthy();
  if (!historyCsvPath) throw new Error('History CSV download path missing');
  const historyCsvText = await readFile(historyCsvPath, 'utf8');
  const historyRows = historyCsvText.trimEnd().split('\r\n');
  expect(historyRows[0]).toBe('\"plant_id\",\"plant_name\",\"timestamp_utc\",\"measurement\",\"unit\",\"value\",\"quality\"');
  expect(historyRows.length).toBeGreaterThan(1);
  expect(historyRows.slice(1).every((row) => row.includes(`"${first.plant_id}"`) && row.includes('"influent_flow"') && /"20\d\d-\d\d-\d\dT.*Z"/.test(row))).toBe(true);
  await historyCsv.saveAs(path.join(evidenceDirectory, `t012-${testInfo.project.name}-history.csv`));

  const historyPngDownload = page.waitForEvent('download');
  await historyFooter.getByRole('button', { name: 'Download PNG' }).click();
  const historyPng = await historyPngDownload;
  const historyPngPath = await historyPng.path();
  expect(historyPngPath).toBeTruthy();
  if (!historyPngPath) throw new Error('History PNG download path missing');
  const historyPngBytes = await readFile(historyPngPath);
  expect(pngDimensions(historyPngBytes).width).toBeGreaterThanOrEqual(1320);
  await historyPng.saveAs(path.join(evidenceDirectory, `t012-${testInfo.project.name}-history.png`));

  await expect(page.getByTestId('forecast-chart')).toBeVisible();
  await expect(page.getByTestId('forecast-chart')).toContainText('Influent flow (gal/h)');
  await expect(page.getByTestId('forecast-chart')).toContainText('Observed→predicted boundary');
  const forecastFooter = page.getByTestId('forecast-export-footer');
  const forecastCsvDownload = page.waitForEvent('download');
  await forecastFooter.getByRole('button', { name: 'Download CSV' }).click();
  const forecastCsv = await forecastCsvDownload;
  const forecastCsvPath = await forecastCsv.path();
  expect(forecastCsvPath).toBeTruthy();
  if (!forecastCsvPath) throw new Error('Forecast CSV download path missing');
  const forecastRows = (await readFile(forecastCsvPath, 'utf8')).trimEnd().split('\r\n');
  expect(forecastRows[0]).toBe('\"plant_id\",\"plant_name\",\"issue_time_utc\",\"target_time_utc\",\"measurement\",\"unit\",\"value\",\"quality\",\"model_version\"');
  expect(forecastRows).toHaveLength(13);
  expect(forecastRows.slice(1).every((row) => row.includes(`"${first.plant_id}"`) && row.includes('"predicted"') && row.includes('"gal/h"'))).toBe(true);
  await forecastCsv.saveAs(path.join(evidenceDirectory, `t012-${testInfo.project.name}-forecast.csv`));

  const forecastPngDownload = page.waitForEvent('download');
  await forecastFooter.getByRole('button', { name: 'Download PNG' }).click();
  const forecastPng = await forecastPngDownload;
  const forecastPngPath = await forecastPng.path();
  expect(forecastPngPath).toBeTruthy();
  if (!forecastPngPath) throw new Error('Forecast PNG download path missing');
  expect(pngDimensions(await readFile(forecastPngPath)).width).toBeGreaterThanOrEqual(1320);
  await forecastPng.saveAs(path.join(evidenceDirectory, `t012-${testInfo.project.name}-forecast.png`));
  await page.screenshot({ path: path.join(evidenceDirectory, `plants-${testInfo.project.name}-ui-m10-exports.png`), fullPage: true });
});

test('SEC-M10-EXPORT logout removes private export actions and cannot reuse stale chart', async ({ page }) => {
  const token = process.env.FLOWSTEAD_TEST_PRINCIPAL_A_TOKEN;
  expect(token).toBeTruthy();
  await installTestAuth(page, { token, principalId: 'test-principal-a' });
  await page.goto('/plants');
  await page.locator('.plant-row').first().click();
  await expect(page.getByTestId('history-export-footer')).toBeVisible();
  await page.getByTestId('sign-out').click();
  await expect(page.getByTestId('sign-in-entry')).toBeVisible();
  await expect(page.getByTestId('history-export-footer')).toHaveCount(0);
  await expect(page.getByTestId('forecast-export-footer')).toHaveCount(0);
});
test('UI-M11-PDF E2E-M12-FILES real download is bounded, safe, and text-readable', async ({ page }, testInfo) => {
  testInfo.annotations.push({ type: 'coverage', description: 'UI-M11-PDF: actual PDF bytes, safe filename, four units/quality flags, twelve targets, model and synthetic source' });
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  await page.goto('/plants');
  const payload = await (await listResponsePromise).json() as { plants: Array<{ plant_id: string; name: string }> };
  const first = payload.plants[0];
  if (!first) throw new Error('Public Plant fixture missing');
  const latestResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith('/latest'));
  await page.locator('.plant-row').first().click();
  const latestPayload = await (await latestResponsePromise).json() as { reading: { measurements: Record<string, { quality: string }> } };
  const qualities = new Set(Object.values(latestPayload.reading.measurements).map((measurement) => measurement.quality));
  const pdfDownload = page.waitForEvent('download');
  await expect(page.getByRole('button', { name: 'Download PDF' })).toBeEnabled();
  await page.getByRole('button', { name: 'Download PDF' }).click();
  const download = await pdfDownload;
  const pdfPath = await download.path();
  expect(pdfPath).toBeTruthy();
  if (!pdfPath) throw new Error('PDF download path missing');
  const bytes = await readFile(pdfPath);
  expect(bytes.subarray(0, 5).toString('ascii')).toBe('%PDF-');
  expect(bytes.length).toBeLessThanOrEqual(256_000);
  expect(download.suggestedFilename()).toMatch(/^flowstead-[a-z0-9-]+-plant-\d+\.pdf$/);
  const extracted = (await exec('pdftotext', [pdfPath, '-'])).stdout;
  const normalizedText = extracted.replace(/\s+/g, ' ');
  expect(normalizedText).toContain(first.name.normalize('NFKD').replace(/[^\x00-\x7F]/g, '?'));
  for (const unit of cardUnits) expect(extracted).toContain(unit);
  for (const quality of qualities) expect(extracted).toContain(quality);
  for (let target = 1; target <= 12; target += 1) expect(extracted).toMatch(new RegExp(`\\b${target}\\b`));
  expect(extracted).toContain('seasonal_naive_24h_v1');
  expect(extracted).toContain('Synthetic source: Flowstead M1 dataset');
  await download.saveAs(path.join(evidenceDirectory, `t012-${testInfo.project.name}-plant-report.pdf`));
  await page.screenshot({ path: path.join(evidenceDirectory, `plants-${testInfo.project.name}-ui-m11-pdf.png`), fullPage: true });
});


test('UI-M9-PARITY signed-out anonymous mode shows Sign in and no open-signup CTA', async ({ page }) => {
  await installTestAuth(page, {});
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  await page.goto('/plants');
  const listResponse = await listResponsePromise;
  expect(listResponse.status()).toBe(200);
  await expect(page.locator('.plant-row')).toHaveCount(5);
  await expect(page.getByTestId('sign-in-entry')).toBeVisible();
  await expect(page.getByTestId('sign-out')).toHaveCount(0);
  await expect(page.getByText(/Sign up|Create account|Register/i)).toHaveCount(0);
});

test('UT-M9-SESSIONS UI-M9-PARITY E2E-M12-PATH invited principal sees only assigned Plants via the real API', async ({ page }, testInfo) => {
  const token = process.env.FLOWSTEAD_TEST_PRINCIPAL_A_TOKEN;
  expect(token).toBeTruthy();
  await installTestAuth(page, { token, principalId: 'test-principal-a' });
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/plants');
  await page.goto('/plants');
  const listResponse = await listResponsePromise;
  expect(listResponse.status()).toBe(200);
  const body = await listResponse.json() as { plants: Array<{ plant_id: string }> };
  expect(body.plants.map((plant) => plant.plant_id).sort()).toEqual(['plant-01', 'plant-02']);
  await expect(page.locator('.plant-marker')).toHaveCount(2);
  await page.screenshot({ path: path.join(evidenceDirectory, `t012-${testInfo.project.name}-private-overview.png`), fullPage: true });
  await expect(page.getByTestId('session-identity')).toContainText('test-principal-a');
  await expect(page.getByTestId('sign-out')).toBeVisible();
  await expect(page.getByTestId('sign-in-entry')).toHaveCount(0);
});

test('UT-M9-SESSIONS E2E-M12-PATH principal B is denied principal A Plant by the actual API (404)', async ({ page }) => {
  const token = process.env.FLOWSTEAD_TEST_PRINCIPAL_B_TOKEN;
  expect(token).toBeTruthy();
  await installTestAuth(page, { token, principalId: 'test-principal-b' });
  await page.goto('/plants/plant-01');
  await expect(page.getByText('Plant not available')).toBeVisible();
  // The real API returns a non-leaking 404 for a principal fetching an
  // unassigned Plant's detail with their own token.
  const status = await page.evaluate(async (bearer) => {
    const response = await fetch('/api/v1/plants/plant-01/latest', { headers: { Authorization: `Bearer ${bearer}` } });
    return response.status;
  }, token);
  expect(status).toBe(404);
});

test('UT-M9-SESSIONS UI-M12-ALL E2E-M12-PATH expired session triggers 401 and returns to public with Session expired', async ({ page }) => {
  const expired = process.env.FLOWSTEAD_TEST_EXPIRED_TOKEN;
  expect(expired).toBeTruthy();
  await installTestAuth(page, { token: expired, principalId: 'test-principal-a' });
  const privateListStatuses: number[] = [];
  page.on('response', (response) => {
    if (new URL(response.url()).pathname === '/api/v1/plants') privateListStatuses.push(response.status());
  });
  await page.goto('/plants');
  await expect(page.getByTestId('session-notice')).toContainText('Session expired');
  await expect(page.getByTestId('sign-in-entry')).toBeVisible();
  expect(privateListStatuses).toContain(401);
});

test('UT-M9-SESSIONS zero-Plant principal sees No plants assigned', async ({ page }) => {
  const token = process.env.FLOWSTEAD_TEST_PRINCIPAL_C_TOKEN;
  expect(token).toBeTruthy();
  await installTestAuth(page, { token, principalId: 'test-principal-c' });
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/plants');
  await page.goto('/plants');
  expect((await listResponsePromise).status()).toBe(200);
  await expect(page.getByText('No plants assigned')).toBeVisible();
});

test('SEC-M9-CACHE IDB-M9-ISOLATE E2E-M12-PATH sign out clears all private IndexedDB rows and restores public', async ({ page }) => {
  const token = process.env.FLOWSTEAD_TEST_PRINCIPAL_A_TOKEN;
  expect(token).toBeTruthy();
  await installTestAuth(page, { token, principalId: 'test-principal-a' });
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/plants');
  await page.goto('/plants');
  await (await listResponsePromise).json();
  await expect(page.getByTestId('session-identity')).toBeVisible();
  // Visiting an authorized detail writes a principal-scoped UI preference.
  const forecastResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/plants/plant-01/forecast');
  await page.locator('.plant-row').first().click();
  expect((await forecastResponsePromise).status()).toBe(200);
  await expect(page.getByTestId('forecast-target')).toHaveCount(12);
  const privateRowsBefore = await page.evaluate(() => new Promise<number>((resolve) => {
    const open = indexedDB.open('flowstead-preferences');
    open.onsuccess = () => {
      const req = open.result.transaction('entries', 'readonly').objectStore('entries').openCursor();
      let count = 0;
      req.onsuccess = () => { const cursor = req.result; if (!cursor) { open.result.close(); resolve(count); } else { if (String(cursor.key).includes('principal:')) count += 1; cursor.continue(); } };
    };
  }));
  expect(privateRowsBefore).toBeGreaterThan(0);
  // sign out clears private rows and returns to public
  const publicListPromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  await page.getByTestId('sign-out').click();
  expect((await publicListPromise).status()).toBe(200);
  await expect(page.getByTestId('sign-in-entry')).toBeVisible();
  await expect.poll(async () => page.evaluate(() => new Promise<number>((resolve) => {
    const open = indexedDB.open('flowstead-preferences');
    open.onsuccess = () => {
      const req = open.result.transaction('entries', 'readonly').objectStore('entries').openCursor();
      let count = 0;
      req.onsuccess = () => { const cursor = req.result; if (!cursor) { open.result.close(); resolve(count); } else { if (String(cursor.key).includes('principal:')) count += 1; cursor.continue(); } };
    };
  }))).toBe(0);
  // reload stays public
  await page.reload();
  await expect(page.getByTestId('sign-in-entry')).toBeVisible();
});
