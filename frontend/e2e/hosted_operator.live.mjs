#!/usr/bin/env node
/**
 * Live browser sign-in validation; never logs passwords, JWTs, input contents,
 * sensitive HTTP bodies, screenshots, traces, or Supabase sessions.
 * Run only from the owner's machine against explicitly approved test users.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { chromium } from 'playwright';

const HOME = process.env.FLOWSTEAD_TEST_PASSWORD_DIR || path.join(os.homedir(), 'Downloads');
const ORIGIN = 'https://flowstead.darizae.dev';
const ACCOUNTS = [
  { email: 'flowstead-test-operator-a@example.invalid', count: 2 },
  { email: 'flowstead-test-operator-b@example.invalid', count: 3 },
];

function ownerPassword(email) {
  const file = path.join(HOME, email + '.txt');
  const st = fs.lstatSync(file);
  if (!st.isFile() || st.isSymbolicLink() || st.uid !== process.getuid() || (st.mode & 0o077) !== 0 || st.size < 8 || st.size > 4096) {
    throw new Error('Operator password file must be owner-only 0600 regular file');
  }
  const password = fs.readFileSync(file, { encoding: 'utf8' }).replace(/[\r\n]+$/, '');
  if (!password || /[\r\n]/.test(password)) {
    throw new Error('Expected one password per operator file');
  }
  return password;
}

async function smoke(browser, account) {
  const context = await browser.newContext({ acceptDownloads: false });
  try {
    const page = await context.newPage();
    page.setDefaultTimeout(20000);
    await page.goto(ORIGIN + '/plants', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.getByTestId('sign-in-entry').click();
    const dialog = page.getByRole('dialog', { name: 'Sign in' });
    await dialog.getByRole('textbox', { name: 'Email' }).fill(account.email);
    await dialog.getByLabel('Password').fill(ownerPassword(account.email));
    await dialog.getByRole('button', { name: 'Sign in' }).click();
    await page.getByTestId('session-identity').waitFor({ state: 'visible', timeout: 30000 });
    await page.locator('.plant-row').first().waitFor({ state: 'visible', timeout: 30000 });
    const actual = await page.locator('.plant-row').count();
    if (actual !== account.count) {
      throw new Error('Incorrect authorized Plant count after browser sign-in');
    }
    console.log('PASS', account.email.endsWith('-a@example.invalid') ? 'operator A' : 'operator B',
      'browser sign-in and scoped Plant count:', actual);
    await page.getByTestId('sign-out').click();
    await page.getByTestId('sign-in-entry').waitFor({ state: 'visible' });
    const publicCount = await page.locator('.plant-row').count();
    if (publicCount !== 5) {
      // Public state may still be fetching after token switch.
      await page.waitForFunction(() => document.querySelectorAll('.plant-row').length === 5, undefined, { timeout: 15000 });
    }
    console.log('PASS signed out, public Plant list restored');
  } finally {
    await context.close(); // ephemeral context, no persistent browser cookies
  }
}

async function main() {
  let browser;
  try {
    browser = await chromium.launch({ channel: 'chrome', headless: true });
    for (const account of ACCOUNTS) {
      await smoke(browser, account);
    }
    console.log('PASS live browser E2E for two operators (no screenshots or credentials saved)');
  } catch (error) {
    // Do NOT print playwright error details/stack, as those can contain
    // entered text, DOM snapshots, Authorization headers and user metadata.
    console.error('BLOCKED live browser smoke:', error?.name || 'UnknownError',
      '— check deployed frontend/API readiness without logging secrets');
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
  }
}

await main();
