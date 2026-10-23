import { test, expect } from '@playwright/test';
import { ADMIN_STATE, DEFAULT_USER_PASSWORD } from './support/env';
import { deleteUserByEmail } from './support/api';

// ใช้อีเมลใหม่ทุกครั้งที่รัน และลบทิ้งเมื่อจบ ไม่กระทบข้อมูลจริง
const email = `e2e-${Date.now()}@playwright.test`;
const username = `e2e${Date.now()}`;
const newPassword = 'e2e-pass-123';

test.describe.configure({ mode: 'serial' });

test.afterAll(async ({ request }) => {
  await deleteUserByEmail(request, email);
});

test.describe('admin', () => {
  test.use({ storageState: ADMIN_STATE });

  test('admin เพิ่มผู้ใช้ใหม่ผ่าน Add User', async ({ page }) => {
  await page.goto('/admin');
  await page.getByRole('button', { name: 'Add User' }).first().click();

  const modal = page.locator('.modal.is-active', { hasText: 'Add New User' });
  await modal.locator('input[type="email"]').fill(email);
  await modal.locator('.modal-card-foot').getByRole('button', { name: 'Add User' }).click();
  await expect(modal).toBeHidden();
  await expect(page.getByText('User added successfully!')).toBeVisible();
  await page.getByRole('button', { name: 'OK' }).click();

  const row = page.locator('tbody tr', { hasText: email });
  await expect(row).toBeVisible();
  await expect(row.getByText('First Login Required')).toBeVisible();
  });
});

test('ผู้ใช้ใหม่ login ครั้งแรกต้องตั้งค่าโปรไฟล์ก่อน', async ({ page }) => {
  await page.goto('/login');
  await page.getByPlaceholder('Enter username').fill(email);
  await page.locator('input[type="password"]').fill(DEFAULT_USER_PASSWORD);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/first-time-setup$/);

  await page.getByPlaceholder('Enter your username').fill(username);
  await page.getByPlaceholder('Enter your full name').fill('E2E Playwright');
  await page.getByPlaceholder('Enter new password (min 6 characters)').fill(newPassword);
  await page.getByPlaceholder('Confirm your new password').fill(newPassword);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/login$/);
});

test('ผู้ใช้ login ด้วยรหัสใหม่แล้วเข้า Dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.getByPlaceholder('Enter username').fill(email);
  await page.locator('input[type="password"]').fill(newPassword);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/home$/);
  await expect(page.locator('nav').getByText('Dashboard')).toBeVisible();
});
