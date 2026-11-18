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
    await expect(page.getByRole('button', { name: new RegExp(plant.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) })).toBeVisible();
  }
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth && document.body.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus-visible')).toBeVisible();
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
