# ทดสอบ end-to-end ด้วย Playwright

ชุดทดสอบนี้ตรวจการทำงานของหน้าเว็บผ่านเบราว์เซอร์จริง ครอบคลุมทั้งฝั่งผู้เรียนและฝั่ง admin แบ่งเป็น 2 กลุ่ม

1. กลุ่มปกติ (project `chromium`) ไม่เรียก Gemini ใช้เวลาประมาณ 3 นาที เหมาะกับการรันทุกครั้งที่แก้โค้ด
2. กลุ่ม AI (project `ai`, tag `@ai`) เรียก Gemini จริง ใช้เวลาหลายสิบนาทีและมีค่า API เพราะต้องรอสร้างคอร์สจาก PDF ครบ 3 ระดับ

ส่วน `tests/` ที่ใช้ Robot Framework ยังใช้สำหรับเก็บภาพหน้าจอประกอบคู่มือเหมือนเดิม

## ติดตั้งครั้งแรก

```bash
cd e2e
npm install
npx playwright install chromium
```

ต้องติดตั้ง backend (`backend/.venv`) และ frontend (`frontend/node_modules`) ไว้ก่อน วิธีที่ง่ายที่สุดคือรัน `./start-all.sh` หนึ่งครั้ง

รหัสผ่าน admin อ่านจาก `ADMIN_EMAIL` และ `ADMIN_PASSWORD` ใน `backend/.env` โดยอัตโนมัติ ถ้าต้องการใช้ค่าอื่น ให้คัดลอก `e2e/.env.example` เป็น `e2e/.env` แล้วกำหนด `E2E_ADMIN_EMAIL` และ `E2E_ADMIN_PASSWORD` กลุ่ม AI ต้องมี Gemini API key ที่ใช้งานได้ในระบบด้วย

## วิธีรัน

```bash
npm test              # รันทั้งหมด รวมกลุ่ม AI
npm run test:fast     # เฉพาะกลุ่มปกติ ไม่เรียก Gemini
npm run test:ai       # เฉพาะกลุ่ม AI
npm run test:video    # รันทั้งหมดและอัดวิดีโอทุก test
npm run test:headed   # เปิดเบราว์เซอร์ให้เห็น
npm run test:ui       # โหมด UI สำหรับไล่ดูทีละขั้น
npm run report        # เปิดรายงาน HTML ของรอบล่าสุด
```

คำสั่งเสริมใส่ต่อท้ายได้ เช่น `npm run test:fast -- --headed` หรือ `npm run test:video -- --project=chromium`

ถ้า ChromaDB, backend และ frontend ยังไม่ทำงาน Playwright จะเปิดให้เองและปิดเมื่อรันเสร็จ ถ้าเปิดไว้อยู่แล้วจะใช้ตัวที่มีอยู่

ทดสอบกับเครื่องอื่น เช่น staging ให้ตั้ง `E2E_BASE_URL` และ `E2E_API_URL` ใน `e2e/.env` ระบบจะไม่เปิด server บนเครื่องนี้

## วิดีโอและหลักฐานเมื่อ test ไม่ผ่าน

ปกติระบบเก็บวิดีโอ ภาพหน้าจอ และ trace เฉพาะ test ที่ไม่ผ่าน ถ้ารันด้วย `npm run test:video` (หรือตั้ง `E2E_VIDEO=on`) จะอัดวิดีโอทุก test ไฟล์ `.webm` อยู่ใน `test-results/` และเปิดดูได้จากรายงาน HTML (`npm run report`) ซึ่งแสดงวิดีโอไว้ในหน้าของแต่ละ test

## ข้อมูลที่ test สร้าง

test สร้างข้อมูลของตัวเองทุกครั้งและลบทิ้งเมื่อจบ ไม่แตะข้อมูลอื่นในระบบ

1. ผู้ใช้ชื่ออีเมล `e2e-...@playwright.test`
2. คอร์สชื่อขึ้นต้นด้วย `E2E` สร้างผ่าน API เดียวกับปุ่ม Submit Quiz มีบทเรียน 2 บทและ quiz 3 ข้อ (ปรนัย เติมคำ อัตนัย)
3. งานสร้างคอร์สจากไฟล์ชื่อ `e2e-<เวลา>.pdf` (ใช้เนื้อหาจาก `tests/Marketing Research.pdf`)
4. การตั้งค่า model ของแต่ละ role ระบบจะคืนค่าเดิมหลังทดสอบ ส่วน API key ทดสอบเฉพาะกรณีใส่ key ผิด ซึ่งระบบปฏิเสธโดยไม่บันทึก

ถ้ารันค้างกลางทาง (เช่นกดหยุด) อาจมีข้อมูลเหล่านี้หลงเหลือ ลบได้จากหน้า admin ตามปกติ

## สิ่งที่ทดสอบ

| ไฟล์ | กลุ่ม | ครอบคลุม |
|---|---|---|
| `login.spec.ts` | ปกติ | หน้า login, รหัสผิด, redirect เมื่อยังไม่ login, logout |
| `user-onboarding.spec.ts` | ปกติ | admin เพิ่มผู้ใช้, ตั้งค่าครั้งแรก, login ด้วยรหัสใหม่ |
| `admin.spec.ts` | ปกติ | ตาราง All Users, ค้นหาผู้ใช้, เมนู All Courses และ Setting |
| `admin-manage.spec.ts` | ปกติ | ค้นหาคอร์ส, รายละเอียดคอร์ส (บทเรียน quiz ผู้ลงทะเบียน), ลบคอร์ส, รายละเอียดผู้ใช้, ลบผู้ใช้ทั้งจากตารางและหน้ารายละเอียด, ปุ่มลบ admin ถูกปิด, หน้า All Quiz Scores, หน้า Setting |
| `learner.spec.ts` | ปกติ | Dashboard, ค้นหาและกรองคอร์ส, ลงทะเบียน, เรียนบทเรียนและ Mark as Complete, เปลี่ยนบท, แท็บ Resume และ Complete, เลื่อนคำถามใน quiz |
| `ai-learning.spec.ts` | AI | แชทกับ AI ในบทเรียนและล้างประวัติ, ทำ quiz ทุกประเภทให้ AI ตรวจและวิเคราะห์ผล, หน้า Quiz Result, คะแนนใน Dashboard, admin ดูผลและคำตอบ |
| `ai-settings.spec.ts` | AI | ปฏิเสธ API key ที่ผิด, แก้ model ราย role, Set All |
| `ai-course-generation.spec.ts` | AI | Import PDF สร้างงาน 3 ระดับ, Preview, แท็บ Agent Logs และ Agent Diagram, Re-Generate คอร์ส, แก้บทเรียนด้วย AI, Create Quiz, Re-Generate quiz, แก้คำถามด้วย AI, Submit Quiz, สถานะ Generated, งานล้มเหลวกับปุ่ม Retry, ลบงาน |

ไฟล์อื่นในโฟลเดอร์

| ไฟล์ | หน้าที่ |
|---|---|
| `playwright.config.ts` | ค่าตั้ง, แบ่ง project, การเปิด server อัตโนมัติ, การอัดวิดีโอ |
| `tests/auth.setup.ts` | login admin ครั้งเดียวแล้วเก็บ session ไว้ที่ `.auth/admin.json` |
| `tests/support/api.ts` | helper เรียก API สำหรับสร้างและลบข้อมูลทดสอบ |
| `tests/support/env.ts` | ค่าคงที่ที่ใช้ร่วมกัน |
