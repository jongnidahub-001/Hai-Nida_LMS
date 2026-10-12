# Backend

API ของ Hai-Nida เขียนด้วย FastAPI เก็บข้อมูลผู้ใช้ คอร์ส และผลแบบทดสอบใน ChromaDB และเรียก Gemini เพื่อสร้างคอร์สและแบบทดสอบจาก PDF

| ไฟล์หรือโฟลเดอร์ | หน้าที่ |
|---|---|
| `app.py` | endpoint ทั้งหมด (`/api/...`) และการยืนยันตัวตนด้วย JWT |
| `conn.py` | เชื่อมต่อ ChromaDB และจัดการข้อมูล |
| `gemini_config.py` | อ่านและบันทึกค่า Gemini (API key และ model ของแต่ละ agent) ที่ admin ตั้งผ่านหน้า Settings |
| `document_chunking.py` | แบ่งและย่อเอกสารยาวก่อนส่งให้ Gemini |
| `agent/create_course/`, `agent/create_quiz/`, `agent/grader/` | agent สร้างคอร์ส สร้างแบบทดสอบ และตรวจคำตอบ |
| `config/` | ที่เก็บ `gemini_settings.json` (ไม่ commit ใช้ `gemini_settings.example.json` เป็นแม่แบบ) |
| `temp/` | ไฟล์ PDF ที่อัปโหลด |

## ค่าที่ต้องตั้ง

คัดลอก `.env.example` เป็น `.env` ค่าที่ใช้มีดังนี้

| ตัวแปร | ความหมาย |
|---|---|
| `GOOGLE_API_KEY` | Gemini API key (ถ้า admin ตั้ง key ในหน้า Settings ระบบจะใช้ key นั้นก่อน) |
| `SECRET_KEY` | key สำหรับเซ็น JWT |
| `ADMIN_EMAIL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` | ใช้สร้าง admin คนแรกตอนเริ่มระบบ ถ้า `ADMIN_PASSWORD` ว่างจะไม่สร้าง admin |
| `CORS_ORIGINS` | origin ที่อนุญาต คั่นด้วย comma เว้นว่างได้ถ้า frontend อยู่ origin เดียวกัน |
| `CHROMA_HOST`, `CHROMA_PORT` | ที่อยู่ของ ChromaDB (default `localhost:8000`) |

## รันบนเครื่อง

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
chroma run --host localhost --port 8000 --path ./chroma-data
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

รัน `chroma` และ `uvicorn` คนละเทอร์มินัล หรือใช้ `./start-all.sh` ที่ root ของ repo ซึ่งเปิดทั้ง ChromaDB, backend และ frontend ให้ เอกสาร API ดูได้ที่ http://localhost:5000/docs

`init_db.py` สร้างผู้ใช้ตัวอย่างที่มีรหัสผ่านซึ่งรู้กันทั่วไป และ `initialize_data.py` สร้างข้อมูลคอร์สตัวอย่าง ใช้บนเครื่องพัฒนาเท่านั้น ห้ามรันบน production
