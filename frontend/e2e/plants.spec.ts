import path from 'node:path';
import { expect, test } from '@playwright/test';

const evidenceDirectory = path.resolve(
  process.env.FLOWSTEAD_EVIDENCE_DIR ?? path.resolve(process.cwd(), '../docs/design/evidence'),
);
const channels = ['dissolved_oxygen', 'effluent_ph', 'influent_flow', 'rainfall'];
const cardLabels = ['Influent flow', 'Rainfall', 'Dissolved oxygen', 'Effluent pH'];
const cardUnits = ['gal/h', 'in/h', 'mg/L', 'unitless'];

function safeFilePart(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

test.beforeEach(async ({ context }) => {
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
});

test.afterEach(async ({ context }, testInfo) => {
  const fileName = `${safeFilePart(testInfo.project.name)}-${safeFilePart(testInfo.title)}.zip`;
  await context.tracing.stop({ path: path.join(evidenceDirectory, fileName) });
});

test('IDB-M7-PREF UI-M7-PARITY public list, detail, back, deep-link and reload', async ({ page }, testInfo) => {
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
    const open = indexedDB.open('flowstead-preferences', 1);
    open.onerror = () => reject(open.error);
    open.onsuccess = () => {
      const database = open.result;
      const transaction = database.transaction('entries', 'readwrite');
      transaction.objectStore('entries').put({ schema: 1, namespace: 'principal:stale', value: {}, savedAt: 1, expiresAt: 1, bytes: 2 }, '1:principal:stale');
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
    const open = indexedDB.open('flowstead-preferences', 1);
    open.onerror = () => reject(open.error);
    open.onsuccess = () => {
      const request = open.result.transaction('entries', 'readonly').objectStore('entries').get('1:principal:stale');
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

test('UI-M8-MAP exact API marker/list identity, attribution, and live style response', async ({ page }) => {
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

test('UI-M8-MAP deterministic style failure keeps API list fallback usable', async ({ page }) => {
  await page.route('**/styles/liberty*', (route) => route.abort());
  const listResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/public/plants');
  await page.goto('/plants');
  const payload = await (await listResponsePromise).json() as { plants: Array<{ plant_id: string }> };
  await expect(page.locator('.plant-row')).toHaveCount(payload.plants.length);
  await expect(page.getByTestId('map-fallback')).toContainText('Map unavailable');
  await expect(page.locator('.plant-marker')).toHaveCount(0);
});

test('UI-M8-MAP deterministic WebGL failure keeps API list fallback usable', async ({ page }) => {
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

test('UI-M8-PARITY desktop and mobile expose four chart channels, units, and 24/72/168 controls', async ({ page }, testInfo) => {
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
});
