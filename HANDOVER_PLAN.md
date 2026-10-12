# แผนเตรียมส่งมอบ Hai-Nida ให้ลูกค้า: ติดตั้งและ deploy อัตโนมัติ

## เป้าหมาย

เราเป็นเจ้าของ GitHub repo นี้ (private) และเพิ่มลูกค้าเป็น collaborator ลูกค้ามี GCP project ของตัวเอง ต้องขึ้นระบบใหม่ทั้งหมดได้ด้วยคำสั่งเดียว

```bash
./scripts/bootstrap-gcp.sh --project <PROJECT_ID>
```

เมื่อจบคำสั่ง ระบบต้องเปิดใช้งานได้ที่ `http://<static IP>` มีรหัส admin ที่สุ่มให้ และ VM ดึงโค้ดใหม่จาก branch `release` เองทุก 5 นาที ไม่ใช้ GitHub Actions ฝั่งลูกค้า หลังจากนั้นลูกค้าไม่ต้อง SSH เข้าเครื่องหรือเขียนไฟล์ config เอง

เหตุที่ VM ต้องดึงเอง: collaborator สิทธิ์ Write ตั้ง GitHub secret และเพิ่ม deploy key ไม่ได้ และ secret ของ repo ชี้ได้แค่ VM เดียว ซึ่งตอนนี้คือระบบเดิมของเรา

## สภาพปัจจุบัน

- รันด้วย `docker-compose.prod.yml` บน VM เดียว มี Caddy, frontend (nginx), backend (FastAPI) และ ChromaDB
- Caddy เป็นจุดเดียวที่เปิดออกภายนอก frontend เรียก API ด้วย path relative `/api` และ backend ใช้ `expose 5000`
- backend อ่าน `.env.prod` ผ่าน `env_file` และ `SECRET_KEY` อ่านจาก environment แล้ว
- `.github/workflows/deploy.yml` deploy ระบบเดิมของเรา (VM `hai-nida-prod`) เมื่อ push เข้า `main` ใช้ secret `VM_HOST`, `VM_USER`, `VM_SSH_KEY`
- มี `backup-chromadb.sh`, `restore-chromadb.sh`, `setup-backup-cron.sh`, `scripts/gcp-static-ip.sh`
- เฟส 1 ถึง 5 เสร็จแล้ว (commit 7666ed76, ac322e93, 34e2fee0, 57d5e56b, 09507b8e) สร้าง branch `release` ในเครื่องแล้ว ยังไม่ push
- ยังไม่ได้ทดสอบบน GCP จริง (หัวข้อ "การตรวจสอบ" ข้อ 3)

## หลักการ

- ใช้ bash + `gcloud` ไม่ใช้ Terraform และไม่ย้ายไป Cloud Run `gh` เป็นตัวเลือก ใช้เมื่อผู้รันเป็น admin ของ repo เท่านั้น
- สคริปต์ทุกตัวต้องรันซ้ำได้ (idempotent) ถ้าทรัพยากรมีอยู่แล้วให้ข้าม ไม่สร้างซ้ำหรือเขียนทับ secret เดิม
- ห้ามมี secret อยู่ใน repo, ใน Docker image หรือใน log ค่าที่พิมพ์ออกจอได้มีเพียงรหัส admin ตอนจบ bootstrap ครั้งแรก และ public key ของ deploy key
- secret ทั้งหมดเก็บที่ Secret Manager แล้ว VM สร้าง `.env.prod` จาก Secret Manager เอง
- ห้ามแตะ VM `hai-nida-prod` ของระบบเดิมและยังไม่ push งานนี้ขึ้น remote
- เอกสารสำหรับลูกค้าเขียนภาษาไทย สุภาพ กระชับ ไม่ใช้อีโมจิ

## เฟส 1: แก้ปัญหาที่ต้องแก้ก่อนส่งมอบ (เสร็จแล้ว)

เลิก track `gemini_settings.json` และข้อมูล/ไฟล์ขยะ, mount volume `backend-config`, ไม่สร้าง admin ด้วยรหัสเริ่มต้น, `name: hai-nida`, Caddy อ่าน `SITE_ADDRESS` จาก `.env.prod` และเพิ่ม `.env.prod.example`

ข้อควรระวังจากเฟส 1: ถ้า `SITE_ADDRESS=` เป็นค่าว่าง Caddy จะอ่านไฟล์ไม่ผ่าน ต้องไม่เขียนบรรทัดนี้เมื่อไม่มีโดเมน

## เฟส 2: สคริปต์ติดตั้ง

### `scripts/bootstrap-gcp.sh`

รันจาก Cloud Shell หรือเครื่องที่มี `gcloud` อยู่ใน clone ของ repo นี้

พารามิเตอร์ (ทุกตัวมีค่า default ยกเว้น project) และรองรับการอ่านจากไฟล์ `deploy.env` ที่ไม่ commit (มี `deploy.env.example` ให้)

| พารามิเตอร์ | default |
|---|---|
| `--project` | (บังคับ) |
| `--region` / `--zone` | `asia-southeast1` / `asia-southeast1-b` |
| `--vm-name` | `hai-nida` |
| `--machine-type` | `e2-medium` |
| `--disk-size` | `30GB` |
| `--domain` | ว่าง (ใช้ IP) |
| `--gemini-key` | ว่าง = สร้าง key ใหม่ให้ |
| `--admin-email` | `admin@<domain หรือ example.com>` |
| `--repo` | อ่านจาก `git remote get-url origin` แปลงเป็นรูปแบบ SSH |
| `--branch` | `release` |
| `--poll-interval` | `5min` |
| `--dry-run` | พิมพ์คำสั่งที่จะรันโดยไม่สร้างอะไร |

ขั้นตอน:

1. ตรวจเงื่อนไข: login `gcloud` แล้ว, project มี billing, ผู้รันมีสิทธิ์พอ (Owner หรือ Editor + Security Admin + Secret Manager Admin)
2. เปิด API: `compute`, `secretmanager`, `apikeys`, `generativelanguage`, `iap`
3. สร้าง static IP, firewall rule TCP 80, 443 จากทุกที่ และ TCP 22 จากช่วง IAP (`35.235.240.0/20`) เท่านั้น ผูกกับ network tag ของ VM
4. สร้าง secret ใน Secret Manager (สร้างเฉพาะที่ยังไม่มี):
   - `hai-nida-google-api-key`: จาก `--gemini-key` หรือสร้างด้วย `gcloud services api-keys create` จำกัดให้ใช้ได้เฉพาะ `generativelanguage.googleapis.com`
   - `hai-nida-secret-key`: สุ่ม 32 byte
   - `hai-nida-admin-password`: สุ่ม
   - `hai-nida-app-config`: ค่าที่ไม่ลับแต่ต้องอยู่ใน `.env.prod` เช่น `ADMIN_EMAIL`, `ADMIN_USERNAME`, `SITE_ADDRESS`, `CORS_ORIGINS`
   - `hai-nida-repo-deploy-key`: private key ของ deploy key แบบ read-only (สร้างด้วย `ssh-keygen` ในไดเรกทอรีชั่วคราว ลบทิ้งหลังเก็บเข้า Secret Manager)
5. deploy key: ถ้าผู้รันมี `gh` และเป็น admin ของ repo ให้เพิ่มด้วย `gh repo deploy-key add` เอง ถ้าไม่ใช่ ให้พิมพ์ public key และขั้นตอนให้เจ้าของ repo เพิ่มที่ Settings > Deploy keys แล้วรอ (ตรวจด้วย `git ls-remote` ผ่าน key นั้น) ก่อนสร้าง VM
6. สร้าง service account `hai-nida-vm` ให้สิทธิ์ `roles/secretmanager.secretAccessor` เฉพาะ secret ข้างบน (ระดับ secret ไม่ใช่ระดับ project) และ `roles/logging.logWriter`
7. สร้าง VM: Ubuntu 24.04 LTS, ใช้ static IP, service account ข้างบน, `--metadata-from-file startup-script=deploy/vm-startup.sh` และ metadata `repo-url`, `repo-branch`, `poll-interval`
8. ตั้ง snapshot schedule ของ boot disk รายวัน เก็บ 7 วัน (`gcloud compute resource-policies create snapshot-schedule`)
9. รอจน `http://<IP>/` และ `http://<IP>/openapi.json` ตอบ 200 (timeout 20 นาที ระหว่างรอแสดง serial console log ล่าสุด)
10. พิมพ์สรุป: URL, admin email, admin password (เฉพาะครั้งแรกที่สร้าง), branch ที่ VM ติดตาม และคำสั่งดู log (`gcloud compute ssh --tunnel-through-iap ... journalctl -u hai-nida-update`)

### `deploy/vm-startup.sh`

รันทุกครั้งที่ VM boot ต้อง idempotent

1. สร้าง user `deploy` ถ้ายังไม่มี และเพิ่มเข้ากลุ่ม `docker`
2. ติดตั้ง Docker Engine กับ compose plugin จาก repository ทางการของ Docker ถ้ายังไม่มี และติดตั้ง `git`, `curl`, `jq`
3. เขียน deploy key จาก Secret Manager ไปที่ `~deploy/.ssh/` (สิทธิ์ `600`) พร้อม `known_hosts` ของ github.com
4. ถ้ายังไม่มี `/opt/hai-nida` ให้ clone `repo-branch` จาก `repo-url` และให้ `deploy` เป็นเจ้าของ
5. ติดตั้ง systemd unit `hai-nida-update.service` และ `hai-nida-update.timer` (ทุก `poll-interval`) ที่เรียก `scripts/vm-update.sh` ในนาม `deploy`
6. เรียก `scripts/vm-update.sh --force` หนึ่งครั้งเพื่อขึ้นระบบ
7. ติดตั้ง cron backup ผ่าน `setup-backup-cron.sh` ถ้ายังไม่มี

อ่าน metadata และ secret ผ่าน metadata server (`http://metadata.google.internal`) กับ Secret Manager REST API โดยใช้ token ของ service account ไม่ต้องพึ่ง `gcloud` บน VM

### `scripts/vm-update.sh`

รันบน VM จาก systemd timer ใช้ `flock` กันรันซ้อน

1. `git fetch` branch ที่ตั้งไว้ ถ้า commit ไม่เปลี่ยนและไม่ได้ส่ง `--force` ให้จบทันที
2. backup ChromaDB, `git reset --hard origin/<branch>`
3. เรียก `scripts/render-env.sh`
4. `docker compose -f docker-compose.prod.yml up -d --build --remove-orphans` และ restart caddy ถ้า Caddyfile เปลี่ยน
5. health check `/` และ `/openapi.json` ถ้าไม่ผ่านให้กลับไป commit เดิมแล้ว build ใหม่ และบันทึก commit ที่ล้มเหลวไว้ ไม่ลองซ้ำจนกว่าจะมี commit ใหม่
6. `docker image prune -f`
7. log ผ่าน journald ไม่ใช้ `set -x` และห้าม echo ค่าใน `.env.prod`

### `scripts/render-env.sh`

ดึง secret ทั้งหมดมาเขียน `.env.prod` แบบ atomic (เขียนไฟล์ชั่วคราวแล้ว `mv`) สิทธิ์ `600` ไม่เขียน `SITE_ADDRESS` เมื่อค่าว่าง

## เฟส 3: workflow deploy ของระบบเดิม

- `deploy.yml` ใช้กับระบบเดิมของเราเท่านั้น ลูกค้าไม่ใช้ ให้ข้ามงานเมื่อไม่ได้ตั้ง secret `VM_HOST` workflow จะได้ไม่ล้มเหลวใน fork หรือ repo ที่ไม่ได้ตั้งค่า
- ไม่เปลี่ยนวิธี deploy ของ VM `hai-nida-prod`

## เฟส 4: สคริปต์เสริม

- `scripts/destroy-gcp.sh --project <ID>`: ลบ VM, IP, firewall rule, service account, secret, snapshot schedule และ API key ที่ bootstrap สร้าง ต้องพิมพ์ชื่อ project ยืนยันก่อนลบ ถามแยกว่าจะลบ backup ด้วยหรือไม่ และเตือนให้เจ้าของ repo ลบ deploy key ของระบบนั้น
- `backup-chromadb.sh` เพิ่ม option อัปโหลดไฟล์ backup ขึ้น GCS bucket `<project>-hai-nida-backups` (bootstrap สร้าง bucket พร้อม lifecycle ลบไฟล์เกิน 30 วัน และให้ service account เขียนได้เฉพาะ bucket นี้) จะได้มี backup นอก VM
- `scripts/rotate-secret.sh <ชื่อ secret>`: เพิ่ม version ใหม่ใน Secret Manager แล้วสั่ง `sudo systemctl start hai-nida-update@force` (หรือเทียบเท่า) ผ่าน `gcloud compute ssh --tunnel-through-iap`
- `scripts/update-now.sh`: สั่ง VM อัปเดตทันทีโดยไม่ต้องรอ timer

## เฟส 5: เอกสารสำหรับลูกค้า

- เขียน `DEPLOY.md` เป็นเอกสารหลักฉบับเดียว: สิ่งที่ต้องมีก่อนเริ่ม (รวมการรับคำเชิญ collaborator และการแจ้งเราเพิ่ม deploy key), คำสั่ง bootstrap, การรับเวอร์ชันใหม่ผ่าน branch `release`, การเปลี่ยน API key หรือรหัส admin, การใช้โดเมน, backup และ restore, การลบระบบ, ค่าใช้จ่ายโดยประมาณ (ระบุว่าเป็นค่าประมาณและให้ตรวจจาก GCP Pricing Calculator) และการแก้ปัญหาที่พบบ่อย
- เขียนขั้นตอนฝั่งเรา (ปล่อยเวอร์ชันด้วยการ merge `main` เข้า `release`, เพิ่ม/ลบ deploy key, เชิญ collaborator) ไว้ในหัวข้อแยกของ `DEPLOY.md`
- `DEPLOYMENT_GUIDE_WEB.md`, `DEPLOYMENT_GUIDE_CLI.md`, `PRODUCTION_DEPLOYMENT.md`, `DEPLOY_AUTOMATION.md`, `docker-setup.md`, `DOCKER_README.md` ให้ย้ายไป `docs/legacy/` หรือรวมเนื้อหาที่ยังใช้ได้เข้า `DEPLOY.md` แล้วถามเจ้าของก่อนลบ
- สร้าง `README.md` ที่ root (ตอนนี้ยังไม่มี) อธิบายระบบสั้นๆ และชี้ไป `DEPLOY.md`

## เฟส 6: ก่อนเชิญลูกค้า

เจ้าของเลือกใช้ repo นี้พร้อมประวัติเดิม collaborator จึงเห็นทุกอย่างที่เคย commit

- ยกเลิก Gemini API key ที่เคยอยู่ใน `backend/config/gemini_settings.json` ที่ Google Cloud Console
- ประวัติยังมีข้อมูลระบบเดิม (`chroma.sqlite3` ที่มีอีเมลและ password hash ของผู้ใช้ และ PDF ที่ผู้ใช้อัปโหลดใน `backend/temp/`) เจ้าของต้องตัดสินใจว่ายอมรับได้หรือจะเปลี่ยนไปใช้ repo ใหม่ที่ไม่มีประวัติ
- สร้าง branch `release` จาก `main`
- สแกน secret ใน tree ปัจจุบัน (`gitleaks detect` หรืออย่างน้อย grep `AIza`, `AQ.`, `-----BEGIN`)

## การตรวจสอบ

- `bash -n` และ `shellcheck` ผ่านทุกสคริปต์ `actionlint` ผ่านสำหรับ workflow `docker compose -f docker-compose.prod.yml config` ผ่านโดยใช้ `.env.prod.example`
- `bootstrap-gcp.sh --dry-run` แสดงคำสั่งครบและไม่สร้างทรัพยากร
- ทดสอบจริงบน GCP project ทดสอบที่ว่าง: bootstrap ผ่านตั้งแต่ต้น, รันซ้ำแล้วไม่สร้างซ้ำและรหัส admin ไม่เปลี่ยน, login ด้วยรหัสที่ได้, อัปโหลด PDF แล้วสร้างคอร์สได้, push commit เล็กๆ เข้า `release` แล้ว VM อัปเดตเองภายใน 5 นาที, commit ที่ทำให้ health check ล้มแล้ว VM กลับไปเวอร์ชันเดิม, reboot VM แล้วระบบกลับมาเอง, ตั้งค่าผ่านหน้า Admin แล้วยังอยู่หลังอัปเดต, rotate `SECRET_KEY` แล้วมีผล, destroy แล้วไม่มีทรัพยากรค้าง
- ค่า secret ต้องไม่ปรากฏใน output ของ bootstrap (ยกเว้นรหัส admin ตอนสร้างครั้งแรก), ใน journald ของ VM และใน `docker history` ของ image

## ลำดับการทำ

ทำทีละเฟสและ commit แยกเฟส (ยังไม่ push) เมื่อจบแต่ละเฟสให้สรุปสิ่งที่เปลี่ยนและสิ่งที่ต้องให้เจ้าของตัดสินใจ การลบเอกสารในเฟส 5 ต้องถามเจ้าของก่อนลงมือ
