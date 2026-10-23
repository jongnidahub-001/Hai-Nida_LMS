import { test as setup, expect } from '@playwright/test';
import { ADMIN_PASSWORD, ADMIN_STATE } from './support/env';
import { adminToken } from './support/api';

// login admin ผ่าน API ครั้งเดียว แล้วเก็บ token ไว้ให้ test อื่นใช้ต่อ
setup('admin session', async ({ page, request }) => {
  expect(ADMIN_PASSWORD, 'ตั้ง E2E_ADMIN_PASSWORD ใน e2e/.env หรือ ADMIN_PASSWORD ใน backend/.env').not.toBe('');
  const token = await adminToken(request);
  await page.goto('/login');
  await page.evaluate((t) => localStorage.setItem('authToken', t), token);
  await page.goto('/admin');
  await expect(page.getByText('All Users', { exact: true }).first()).toBeVisible();
  await page.context().storageState({ path: ADMIN_STATE });
});
