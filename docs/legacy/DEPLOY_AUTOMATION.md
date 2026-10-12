# Deploy อัตโนมัติด้วย GitHub Actions

ระบบยังรันด้วย `docker-compose.prod.yml` บน VM `hai-nida-prod` ตัวเดิม (asia-southeast1-b) ที่เปลี่ยนคือเมื่อ push เข้า branch `main` แล้ว GitHub Actions จะ SSH เข้า VM แล้วทำขั้นตอนต่อไปนี้ให้เอง

1. backup ChromaDB ด้วย `backup-chromadb.sh`
2. ดึงโค้ดล่าสุด (`git reset --hard origin/main`)
3. build และ start ใหม่ด้วย `docker compose -f docker-compose.prod.yml up -d --build`
4. ตรวจว่าหน้าเว็บและ backend ตอบได้ ถ้าไม่ผ่าน job จะ fail และแสดง log ของ backend

การแก้เฉพาะเอกสาร (`*.md`, `*.docx`, `docs/`) หรือไฟล์ทดสอบจะไม่ trigger deploy และสั่ง deploy เองได้จากแท็บ Actions > Deploy to VM > Run workflow

ตอนนี้ยังไม่ใช้โดเมน เข้าใช้งานผ่าน `http://<static IP>` โดย frontend เรียก API ด้วย path relative (`/api/...`) ผ่าน Caddy จึงไม่ต้องตั้ง `REACT_APP_API_BASE_URL` และไม่ต้อง build ใหม่เมื่อ IP หรือโดเมนเปลี่ยน

## ตั้งค่าครั้งแรก

### 1. ทำ static IP

รันจากเครื่องที่ login `gcloud` ไว้แล้ว สคริปต์จะแปลง IP ปัจจุบันของ VM เป็น static โดยไม่ต้องหยุดเครื่อง ถ้าเป็น static อยู่แล้วจะไม่ทำอะไร

```bash
./scripts/gcp-static-ip.sh hai-nida-prod asia-southeast1-b
```

### 2. เตรียม VM

SSH เข้า VM แล้วตรวจสอบดังนี้

```bash
cd /opt/hai-nida
git status                 # ต้องเป็น git clone ของ repo นี้
ls .env.prod               # ไฟล์ secret ยังอยู่บน VM ที่เดิม workflow ไม่ได้แตะ
cp Caddyfile ~/Caddyfile.bak   # เก็บของเดิมไว้ เพราะ deploy ครั้งแรกจะใช้ Caddyfile จาก repo แทน
git fetch origin main      # ต้องไม่ถามรหัสผ่าน
```

ถ้า `git fetch` ถามรหัสผ่าน (repo เป็น private) ให้เพิ่ม deploy key แบบ read-only ให้ VM ที่ GitHub > Settings > Deploy keys แล้วเปลี่ยน remote เป็น `git@github.com:DiffChotipong/Hai-Nida.git`

backend อ่าน `.env.prod` ผ่าน `env_file` ใน `docker-compose.prod.yml` ไฟล์นี้จึงต้องมีอยู่เสมอ ค่าที่ควรมีคือ `GOOGLE_API_KEY`, `SECRET_KEY` และ `ADMIN_EMAIL`/`ADMIN_USERNAME`/`ADMIN_PASSWORD` (ใช้เฉพาะตอนยังไม่มี admin ในระบบ) ส่วน `REACT_APP_API_BASE_URL` ลบออกได้ และ `CORS_ORIGINS` เว้นว่างได้ เพราะ frontend กับ backend อยู่ origin เดียวกันแล้ว

ก่อนหน้านี้ backend ไม่ได้อ่าน `SECRET_KEY` จาก environment (ใช้ค่าที่ฝังในโค้ด) ตอนนี้แก้ให้อ่านแล้ว ถ้าใน `.env.prod` ตั้งค่าไว้ หลัง deploy ครั้งแรกผู้ใช้ทุกคนต้อง login ใหม่หนึ่งครั้ง ถ้ายังไม่ได้ตั้ง ให้สร้างด้วย `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

`GOOGLE_API_KEY` ที่เคย commit อยู่ใน `backend/.env` ยังอยู่ในประวัติ git ให้สร้าง key ใหม่ที่ Google AI Studio ใส่ใน `.env.prod` แล้วลบ key เดิมทิ้ง

หมายเหตุ: workflow ใช้ `git reset --hard` ไฟล์ที่ track ใน git ซึ่งแก้ไว้บน VM จะถูกแทนด้วยของใน repo ทุกครั้ง การแก้ config ให้ทำผ่าน repo เท่านั้น ยกเว้น `.env.prod` และ `backups/` ซึ่งไม่อยู่ใน git

### 3. สร้าง SSH key สำหรับ deploy

```bash
ssh-keygen -t ed25519 -C "github-deploy" -f hinida-deploy -N ""
```

นำ `hinida-deploy.pub` ไปต่อท้าย `~/.ssh/authorized_keys` ของ user บน VM ที่เป็นเจ้าของ `/opt/hai-nida` user นั้นต้องอยู่ในกลุ่ม docker ด้วย

```bash
sudo usermod -aG docker $USER   # ถ้ายังไม่อยู่ในกลุ่ม แล้ว logout/login ใหม่
```

ถ้าเปิด OS Login ไว้ที่ VM หรือ project ระบบจะไม่อ่าน `authorized_keys` ต้องปิด OS Login ของ VM นี้ หรือเปลี่ยนไปใช้วิธี IAP แทน

### 4. ตั้ง GitHub Secrets

ที่ repo > Settings > Secrets and variables > Actions > New repository secret

| Secret | ค่า |
|---|---|
| `VM_HOST` | static IP ของ VM |
| `VM_USER` | ชื่อ user บน VM จากข้อ 3 |
| `VM_SSH_KEY` | เนื้อหาไฟล์ `hinida-deploy` (private key) ทั้งไฟล์ |

ใส่แล้วลบไฟล์ private key ออกจากเครื่อง

### 5. Firewall

ต้องเปิด TCP 22 ขาเข้า (rule `default-allow-ssh` ปกติเปิดไว้อยู่แล้ว) และ TCP 80 สำหรับผู้ใช้

port 5000 ไม่ต้องเปิดแล้ว เพราะ backend ไม่ได้เปิดออกนอก Docker network อีก หลัง deploy ครั้งแรกผ่าน ให้ลบ firewall rule ของ port 5000 ทิ้ง

### 6. ทดสอบ

ไปที่ Actions > Deploy to VM > Run workflow แล้วเปิด `http://<static IP>` ตรวจว่า login และเรียกข้อมูลได้

## Rollback

`git revert <commit>` แล้ว push เข้า `main` ระบบจะ deploy เวอร์ชันก่อนหน้าให้เอง ถ้าข้อมูล ChromaDB เสีย ใช้ `restore-chromadb.sh` กับไฟล์ใน `backups/chromadb/` ซึ่ง backup ให้ทุกครั้งก่อน deploy

## ข้อควรระวัง

ตอน deploy backend จะ restart งาน batch ที่กำลังประมวลผลจะถูกตัด ควร deploy ช่วงที่ไม่มีงานค้าง

## เมื่อจะใช้โดเมน

สร้าง A record ชี้ไปที่ static IP แล้วเปลี่ยนบรรทัด `:80 {` ใน `Caddyfile` เป็นชื่อโดเมน เปิด TCP 443 แล้ว push Caddy จะออกใบรับรอง HTTPS ให้อัตโนมัติ ไม่ต้อง build frontend ใหม่
