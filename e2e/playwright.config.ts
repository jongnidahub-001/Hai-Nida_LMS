import { defineConfig, devices } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

// ค่า admin อ่านจาก e2e/.env ก่อน ถ้าไม่มีจะใช้ ADMIN_EMAIL/ADMIN_PASSWORD จาก backend/.env
for (const file of ['.env', '../backend/.env']) {
  const full = path.resolve(__dirname, file);
  if (fs.existsSync(full)) process.loadEnvFile(full);
}

const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:3000';
const API_URL = process.env.E2E_API_URL ?? 'http://localhost:5000';
process.env.E2E_API_URL = API_URL;
process.env.E2E_ADMIN_EMAIL ??= process.env.ADMIN_EMAIL || 'admin@admin.com';
process.env.E2E_ADMIN_PASSWORD ??= process.env.ADMIN_PASSWORD;

// ถ้าตั้ง E2E_BASE_URL ไปที่เครื่องอื่น (เช่น staging) จะไม่เปิด server บนเครื่องนี้
const startLocalServers = !process.env.E2E_BASE_URL;
const backendDir = path.resolve(__dirname, '../backend');
const frontendDir = path.resolve(__dirname, '../frontend');

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    // กันไม่ให้ click หรือ fill ค้างจนถึง timeout ของทั้ง test เมื่อหา element ไม่เจอ
    actionTimeout: 60_000,
    viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    // ปกติเก็บวิดีโอเฉพาะ test ที่ไม่ผ่าน ตั้ง E2E_VIDEO=on เพื่ออัดทุก test
    video: {
      mode: (process.env.E2E_VIDEO as 'on' | 'off' | 'retain-on-failure') ?? 'retain-on-failure',
      size: { width: 1440, height: 900 },
    },
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
      dependencies: ['setup'],
      grepInvert: /@ai/,
    },
    {
      // test ที่เรียก Gemini จริง ใช้เวลานานและมีค่า API
      name: 'ai',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
      dependencies: ['setup'],
      grep: /@ai/,
      timeout: 10 * 60_000,
    },
  ],
  webServer: startLocalServers
    ? [
        {
          command: '.venv/bin/chroma run --host localhost --port 8000 --path ./chroma-data',
          cwd: backendDir,
          url: 'http://localhost:8000/api/v2/heartbeat',
          reuseExistingServer: true,
          timeout: 60_000,
        },
        {
          command: '.venv/bin/uvicorn app:app --host 127.0.0.1 --port 5000',
          cwd: backendDir,
          url: `${API_URL}/api/hello`,
          reuseExistingServer: true,
          timeout: 120_000,
        },
        {
          command: 'npm start',
          cwd: frontendDir,
          url: BASE_URL,
          env: { BROWSER: 'none', PORT: '3000' },
          reuseExistingServer: true,
          timeout: 180_000,
        },
      ]
    : undefined,
});
