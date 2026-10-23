import { test, expect } from '@playwright/test';
import { ADMIN_STATE } from './support/env';

test.use({ storageState: ADMIN_STATE });

test.describe('เมนู admin', () => {
  test('หน้า All Users แสดงตารางผู้ใช้', async ({ page }) => {
    await page.goto('/admin');
    await expect(page.locator('table thead th', { hasText: 'Email' })).toBeVisible();
    await expect(page.locator('table tbody tr', { hasText: 'admin' }).first()).toBeVisible();
  });

  test('ค้นหาผู้ใช้ด้วยคำที่ไม่มีอยู่ต้องแสดง No users found', async ({ page }) => {
    await page.goto('/admin');
    await page.getByPlaceholder('Search users...').fill('no-such-user-xyz');
    await expect(page.getByText('No users found')).toBeVisible();
  });

  test('เมนู All Courses เปิดหน้า Course Management', async ({ page }) => {
    await page.goto('/admin');
    await page.locator('nav').getByText('All Courses').click();
    await expect(page).toHaveURL(/\/admin\/courses$/);
    await expect(page.getByText('Course Management')).toBeVisible();
    await expect(page.getByText('Import Document').first()).toBeVisible();
  });

  test('เมนู Setting เปิดหน้า Gemini API Settings', async ({ page }) => {
    await page.goto('/admin');
    await page.locator('nav').getByText('Setting').click();
    await expect(page).toHaveURL(/\/admin\/settings$/);
    await expect(page.getByText('Gemini API Settings')).toBeVisible();
  });
});
