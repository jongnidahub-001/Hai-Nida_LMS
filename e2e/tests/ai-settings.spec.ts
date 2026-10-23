import { test, expect, Page } from '@playwright/test';
import { ADMIN_STATE, API_URL } from './support/env';
import { adminToken } from './support/api';

// ทุก test ในไฟล์นี้ให้ backend ตรวจ key หรือ model กับ Gemini จริง และคืนค่าเดิมเมื่อจบ
test.use({ storageState: ADMIN_STATE });
test.describe.configure({ mode: 'serial' });

const ROLES = ['planner', 'writer', 'grader'] as const;

async function closeAlert(page: Page, text: RegExp | string) {
  await expect(page.getByText(text)).toBeVisible({ timeout: 90_000 });
  await page.getByRole('button', { name: 'OK' }).click();
}

test.describe('ตั้งค่า Gemini', { tag: '@ai' }, () => {
  let original: Record<string, string>;

  test.beforeAll(async ({ request }) => {
    const res = await request.get(`${API_URL}/api/admin/gemini/role-models`, {
      headers: { Authorization: `Bearer ${await adminToken(request)}` },
      timeout: 120_000,
    });
    original = await res.json();
  });

  test.afterAll(async ({ request }) => {
    const headers = { Authorization: `Bearer ${await adminToken(request)}` };
    for (const role of ROLES) {
      if (original?.[`${role}_model`]) {
        await request.put(`${API_URL}/api/admin/gemini/role-model`, { headers, data: { role, model: original[`${role}_model`] }, timeout: 90_000 });
      }
    }
  });

  test('ใส่ API key ที่ไม่ถูกต้องต้องถูกปฏิเสธและ key เดิมไม่เปลี่ยน', async ({ page }) => {
    await page.goto('/admin/settings');
    await expect(page.getByText('Gemini API Settings')).toBeVisible({ timeout: 60_000 });
    const key = page.locator('code').first();
    await expect(key).not.toHaveText('');
    const before = await key.textContent();

    await page.getByRole('button', { name: /Change Key|Set Key/ }).click();
    const modal = page.locator('.modal.is-active');
    await modal.getByPlaceholder(/Enter your Gemini API key/).fill('AIzaSyE2EInvalidKey000000000000000000000');
    await modal.getByRole('button', { name: 'Save' }).click();

    await closeAlert(page, /Invalid API key|Failed to update API key/);
    await page.reload();
    await expect(page.locator('code').first()).toHaveText(before!, { timeout: 60_000 });
  });

  test('แก้ model ของ Planner แล้วบันทึกได้', async ({ page }) => {
    await page.goto('/admin/settings');
    await page.getByRole('button', { name: 'Edit' }).first().click({ timeout: 60_000 });
    const modal = page.locator('.modal.is-active');
    await modal.locator('select').selectOption(original.planner_model);
    await modal.getByRole('button', { name: 'Save' }).click();
    await closeAlert(page, /Model for planner updated successfully/);
  });

  test('Set All ตั้ง model เดียวกันให้ทุก role ได้', async ({ page }) => {
    await page.goto('/admin/settings');
    await page.getByRole('button', { name: 'Set All' }).click({ timeout: 60_000 });
    const modal = page.locator('.modal.is-active', { hasText: 'Set All Roles to Same Model' });
    await modal.locator('select').selectOption(original.planner_model);
    await modal.getByRole('button', { name: 'Save' }).click();
    await expect(modal).toBeHidden({ timeout: 90_000 });

    await page.reload();
    await expect(page.getByText('Gemini API Settings')).toBeVisible({ timeout: 60_000 });
    const roleModels = page.locator('.column.is-4 code');
    await expect(roleModels).toHaveText([original.planner_model, original.planner_model, original.planner_model]);
  });
});
