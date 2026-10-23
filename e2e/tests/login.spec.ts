import { test, expect } from '@playwright/test';
import { ADMIN_EMAIL, ADMIN_PASSWORD } from './support/env';

test.describe('หน้า login', () => {
  test('แสดงฟอร์ม sign in', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
    await expect(page.getByPlaceholder('Enter username')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeEnabled();
  });

  test('รหัสผ่านผิดต้องแสดงข้อความ error และอยู่หน้าเดิม', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('Enter username').fill(ADMIN_EMAIL);
    await page.locator('input[type="password"]').fill('wrong-password');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page.locator('.login-form-card .help.is-danger')).toBeVisible();
    await expect(page).toHaveURL(/\/login$/);
  });

  test('ยังไม่ login เปิดหน้า admin ต้องถูกส่งกลับไปหน้า login', async ({ page }) => {
    await page.goto('/admin');
    await expect(page).toHaveURL(/\/login$/);
  });

  test('admin login แล้วเข้าหน้า All Users และ logout ได้', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('Enter username').fill(ADMIN_EMAIL);
    await page.locator('input[type="password"]').fill(ADMIN_PASSWORD);
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/admin$/);

    await page.getByRole('button', { name: 'Logout' }).click();
    await expect(page).toHaveURL(/\/login$/);
    expect(await page.evaluate(() => localStorage.getItem('authToken'))).toBeNull();
  });
});
