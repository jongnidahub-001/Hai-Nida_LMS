export const API_URL = process.env.E2E_API_URL!;
export const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL!;
export const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? '';
export const ADMIN_STATE = '.auth/admin.json';

// รหัสผ่านเริ่มต้นที่ backend ตั้งให้ผู้ใช้ที่ admin เพิ่ม (backend/app.py, /api/admin/add-user)
export const DEFAULT_USER_PASSWORD = 'haionetime1234';
