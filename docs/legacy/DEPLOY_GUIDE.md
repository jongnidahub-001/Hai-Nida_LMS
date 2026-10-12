# คู่มือการ Deploy Website Hai-Nida

คู่มือนี้ครอบคลุมการ deploy แอปพลิเคชัน Hai-Nida (Learning Management System) ขึ้น production

---

## สถาปัตยกรรม

```
Internet → Caddy (80/443) → Frontend (nginx) → Backend (FastAPI)
                              ↓                    ↓
                         Static files          ChromaDB (Vector DB)
                         /api/* → backend:5000
```

| Service   | พอร์ต | คำอธิบาย                        |
|-----------|-------|----------------------------------|
| Caddy     | 80, 443 | Reverse proxy, Auto HTTPS      |
| Frontend  | 80 (internal) | React + nginx, รับ /api/* ส่งต่อ backend |
| Backend   | 5000  | FastAPI API                     |
| ChromaDB  | 8000  | Vector database สำหรับ AI       |

---

## ข้อกำหนดเบื้องต้น

- **Docker** และ **Docker Compose**
- เซิร์ฟเวอร์ที่มี public IP หรือ domain ชี้มาที่เซิร์ฟเวอร์
- ถ้าใช้ domain: ชี้ A record มาที่ IP ของเซิร์ฟเวอร์

---

## 1. เตรียมไฟล์ก่อน Deploy

### 1.1 สร้าง Caddyfile

สร้างไฟล์ `Caddyfile` ที่โฟลเดอร์ root ของโปรเจกต์ (ถ้ายังไม่มี):

```caddy
hai-nida.com {
    reverse_proxy frontend:80
}
```

- แทน `hai-nida.com` ด้วย domain ของคุณ
- Caddy จะขอ SSL (Let's Encrypt) ให้อัตโนมัติ
- ถ้าใช้ IP อย่างเดียว (ยังไม่มี domain): ใช้ `http://:80` แทน

### 1.2 ตั้งค่า API URL (Frontend)

แก้ไข `docker-compose.prod.yml` บรรทัด API URL:

```yaml
frontend:
  build:
    args:
      - REACT_APP_API_BASE_URL=https://hai-nida.com
```

ให้ตรงกับ domain ที่ใช้จริง เช่น:

- `https://your-domain.com` ถ้าใช้ domain
- `http://YOUR_SERVER_IP` ถ้าใช้ IP โดยตรง

### 1.3 ตั้งค่า Backend (Environment)

ตรวจสอบ `docker-compose.prod.yml`:

- `GOOGLE_API_KEY` – API Key ของ Google Gemini (ต้องมี)
- `CHROMA_HOST`, `CHROMA_PORT` – ไม่ต้องแก้ ถ้าใช้ config เดิม

ถ้าใช้ `.env` ให้สร้างไฟล์ `.env` ที่ root โปรเจกต์ หรือส่ง env ใน compose:

```env
GOOGLE_API_KEY=your-google-api-key
SECRET_KEY=your-secret-key-change-in-production
```

---

## 2. Deploy ครั้งแรก

### 2.1 Clone และเข้าหน้าโปรเจกต์

```powershell
cd C:\Sandbox\Hai-Nida
```

### 2.2 Build และ Start

```powershell
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### 2.3 ตรวจสอบสถานะ

```powershell
docker-compose -f docker-compose.prod.yml ps
```

ควรเห็นทุก service เป็น `Up`:

```
NAME                STATUS
hai-nida-caddy-1    Up
hai-nida-frontend-1 Up
hai-nida-backend-1  Up
hai-nida-chromadb-1 Up
```

---

## 3. Deploy หลังอัปเดตโค้ด

### 3.1 อัปเดต Frontend เท่านั้น

```powershell
docker-compose -f docker-compose.prod.yml build --no-cache frontend
docker-compose -f docker-compose.prod.yml up -d
```

### 3.2 อัปเดต Backend เท่านั้น

```powershell
docker-compose -f docker-compose.prod.yml build --no-cache backend
docker-compose -f docker-compose.prod.yml up -d
```

### 3.3 อัปเดตทั้งระบบ

```powershell
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

**ไม่ต้องรัน `docker-compose down` ก่อน**  
`up -d` จะ recreate เฉพาะ containers ที่ image เปลี่ยน มี downtime ประมาณ 1–3 วินาที

---

## 4. คำสั่งที่ใช้บ่อย

### 4.1 ดูสถานะและ Logs

```powershell
# สถานะ containers
docker-compose -f docker-compose.prod.yml ps

# Logs ทั้งหมด
docker-compose -f docker-compose.prod.yml logs -f

# Logs service เดียว
docker-compose -f docker-compose.prod.yml logs -f frontend
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f caddy
```

### 4.2 หยุดและเริ่มใหม่

```powershell
# หยุด
docker-compose -f docker-compose.prod.yml down

# เริ่มใหม่
docker-compose -f docker-compose.prod.yml up -d
```

### 4.3 ตรวจสอบ Cache Headers (หลัง deploy frontend)

```powershell
curl -I https://hai-nida.com/
```

ควรเห็น:

```
Cache-Control: no-cache, no-store, must-revalidate
Pragma: no-cache
Expires: 0
```

---

## 5. Data Persistence

ข้อมูลจะถูกเก็บในโฟลเดอร์เหล่านี้:

| ข้อมูล        | โฟลเดอร์              |
|---------------|------------------------|
| ChromaDB      | `./chroma-data/`      |
| Backend temp  | `./backend/temp/`     |
| Backend Chroma | `./backend/chroma_db/` |
| Caddy (SSL)   | Docker volume `caddy_data` |

**ควรสำรอง (backup):**

- `./chroma-data/` – ข้อมูล vector
- ฐานข้อมูล/ไฟล์อื่นที่ใช้เก็บ user / course

---

## 6. การแก้ปัญหาเบื้องต้น

### 6.1 หน้าเว็บเก่า / ไม่เห็นฟีเจอร์ใหม่

- อาจเกิดจาก cache  
- Hard refresh: `Ctrl+Shift+R` (Windows) หรือ `Cmd+Shift+R` (Mac)
- ตรวจสอบว่า deploy frontend แล้ว และ `curl -I` แสดง `Cache-Control: no-cache`

### 6.2 Backend เชื่อมต่อ ChromaDB ไม่ได้

```powershell
docker-compose -f docker-compose.prod.yml ps chromadb
docker-compose -f docker-compose.prod.yml logs chromadb
```

ตรวจว่า ChromaDB ขึ้นก่อน backend และ network ถูกต้อง

### 6.3 SSL / HTTPS ไม่ทำงาน

- ตรวจว่า domain ชี้มาที่เซิร์ฟเวอร์ถูกต้อง
- ตรวจว่า port 80 และ 443 เปิด
- ดู log Caddy: `docker-compose -f docker-compose.prod.yml logs caddy`

### 6.4 Port ถูกใช้งานอยู่แล้ว

แก้ `docker-compose.prod.yml`:

```yaml
caddy:
  ports:
    - "8080:80"
    - "8443:443"
```

### 6.5 Build ล้มเหลว / dependency ผิด

```powershell
docker-compose -f docker-compose.prod.yml down
docker system prune -a
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

---

## 7. โครงสร้างไฟล์ที่เกี่ยวกับ Deploy

| ไฟล์ | หน้าที่ |
|------|---------|
| `docker-compose.prod.yml` | config production |
| `Caddyfile` | reverse proxy + HTTPS |
| `frontend/Dockerfile.prod` | build React + nginx |
| `frontend/nginx.conf` | config nginx (cache, SPA, API proxy) |
| `backend/Dockerfile` | build FastAPI |

---

## 8. Checklist ก่อน Go Live

- [ ] แก้ `REACT_APP_API_BASE_URL` ใน `docker-compose.prod.yml`
- [ ] แก้ domain ใน `Caddyfile`
- [ ] ตั้งค่า `GOOGLE_API_KEY` ให้ถูกต้อง
- [ ] ตั้งค่า `SECRET_KEY` สำหรับ production (ไม่ใช้ค่า default)
- [ ] เปลี่ยนรหัส admin ในระบบ (ถ้ามี)
- [ ] Backup โฟลเดอร์ `chroma-data` และข้อมูลสำคัญ
- [ ] ทดสอบหน้า Login, ลงทะเบียน, และ flow การเรียนหลักๆ
