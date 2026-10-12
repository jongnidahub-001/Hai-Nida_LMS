# Hai-Nida LMS

ระบบจัดการการเรียนรู้ที่ใช้ Gemini สร้างคอร์สและแบบทดสอบจากเอกสาร PDF ผู้ดูแลอัปโหลดเอกสาร ระบบจะสร้างบทเรียนหลายระดับความยาก แบบทดสอบ และวิเคราะห์ผลให้ผู้เรียน

ส่วนประกอบหลัก

| โฟลเดอร์ | หน้าที่ |
|---|---|
| `frontend/` | เว็บแอป React |
| `backend/` | API ด้วย FastAPI และ agent ที่เรียก Gemini |
| `scripts/`, `deploy/` | สคริปต์ติดตั้งและดูแลระบบบน Google Cloud |
| `tests/` | ทดสอบ end-to-end ด้วย Robot Framework |

ใน production ระบบรันด้วย `docker-compose.prod.yml` ซึ่งมี Caddy, frontend, backend และ ChromaDB บน VM เครื่องเดียว

## ติดตั้งบน Google Cloud

ดู [DEPLOY.md](DEPLOY.md) (ฉบับ Word: `คู่มือการติดตั้งและดูแลระบบ.docx`) ครอบคลุมการติดตั้งด้วยคำสั่งเดียว การรับเวอร์ชันใหม่ การเปลี่ยน API key การ backup และค่าใช้จ่าย

## รันบนเครื่องสำหรับพัฒนา

1. คัดลอก `backend/.env.example` เป็น `backend/.env` แล้วใส่ `GOOGLE_API_KEY`, `SECRET_KEY` และ `ADMIN_PASSWORD` (ถ้าไม่ใส่ `ADMIN_PASSWORD` ระบบจะไม่สร้าง admin)
2. รัน `./start-all.sh` (ต้องมี Python 3 และ Node.js) สคริปต์จะติดตั้ง dependency แล้วเปิด ChromaDB, backend และ frontend
3. เปิด http://localhost:3000 (API อยู่ที่ http://localhost:5000/docs)
