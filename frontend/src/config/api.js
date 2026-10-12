// API Configuration
// Production: ไม่ต้องตั้งค่า ใช้ path relative (/api/...) ผ่าน Caddy บนโดเมนเดียวกับหน้าเว็บ
// Development: ตั้ง REACT_APP_API_BASE_URL=http://localhost:5000 ใน frontend/.env
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL ?? '';

export { API_BASE_URL }; 