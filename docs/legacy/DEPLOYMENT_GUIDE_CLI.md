# Deployment Guide (CLI Version) - Hai-Nida LMS

คู่มือการ Deploy ระบบ Hai-Nida LMS บน Google Cloud Platform ผ่าน **Command Line Interface (gcloud CLI)**

> 📌 ดูเวอร์ชัน Web Console ได้ที่ [DEPLOYMENT_GUIDE_WEB.md](./DEPLOYMENT_GUIDE_WEB.md)
>
> หลังติดตั้งครั้งแรกแล้ว การ deploy ครั้งต่อไปทำอัตโนมัติผ่าน GitHub Actions ดู [DEPLOY_AUTOMATION.md](./DEPLOY_AUTOMATION.md)

## สารบัญ

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Step 1: สร้าง Google Cloud VM](#step-1-สร้าง-google-cloud-vm)
- [Step 2: ติดตั้ง Docker และ Docker Compose](#step-2-ติดตั้ง-docker-และ-docker-compose)
- [Step 3: ตั้งค่า Google Gemini API Key](#step-3-ตั้งค่า-google-gemini-api-key)
- [Step 4: ตั้งค่า DNS (ไม่บังคับ)](#step-4-ตั้งค่า-dns-ไม่บังคับ)
- [Step 5: เตรียม Production Files](#step-5-เตรียม-production-files)
- [Step 6: Deploy ด้วย Docker Compose](#step-6-deploy-ด้วย-docker-compose)
- [Step 7: ตรวจสอบและ Monitor](#step-7-ตรวจสอบและ-monitor)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)

---

## Overview

Hai-Nida เป็นระบบ LMS (Learning Management System) ที่ใช้ AI ช่วยสร้างคอร์สเรียนและแบบทดสอบอัตโนมัติ

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | React 19 + Bulma CSS + Nginx |
| Backend | FastAPI (Python 3.11) + Uvicorn |
| Database | ChromaDB (Vector Database) |
| LLM | Google Gemini (gemini-2.5-flash) |
| Reverse Proxy | Caddy (Auto HTTPS) |
| Container | Docker + Docker Compose |
| Cloud | Google Cloud Platform (Compute Engine) |


---

## Architecture

```
                    Internet
                       │
                       ▼
              ┌────────────────┐
              │   DNS (Custom) │
              └───────┬────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │  Google Compute Engine  │
         │         (VM)            │
         │                         │
         │  ┌───────────────────┐  │
         │  │  Caddy (Port 80/  │  │
         │  │  443 Auto HTTPS)  │  │
         │  └────────┬──────────┘  │
         │           │             │
         │     ┌─────┴──────┐     │
         │     ▼            ▼     │
         │  ┌───────┐ ┌────────┐  │
         │  │Frontend│ │Backend │  │
         │  │(Nginx) │ │(FastAPI│  │
         │  │Port 80 │ │Port    │  │
         │  │internal│ │5000 in)│  │
         │  └───────┘ └───┬────┘  │
         │                 │       │
         │                 ▼       │
         │          ┌──────────┐   │
         │          │ ChromaDB │   │
         │          │(Port 8000│   │
         │          └──────────┘   │
         └─────────────────────────┘
```

### Services

1. **Caddy** - Reverse proxy พร้อม Auto HTTPS (Let's Encrypt)
2. **Frontend** - React app ที่ build แล้ว serve ผ่าน Nginx
3. **Backend** - FastAPI REST API + AI Agent (Gemini)
4. **ChromaDB** - Vector database สำหรับเก็บข้อมูลคอร์ส, ผู้ใช้, และ embeddings

---

## Prerequisites

- Google Cloud account พร้อม billing enabled
- ติดตั้ง [Google Cloud CLI (gcloud)](https://cloud.google.com/sdk/docs/install) บนเครื่อง local
- Google Gemini API Key จาก [Google AI Studio](https://aistudio.google.com/apikey)
- Domain name ที่จัดการ DNS records ได้ (Caddy ต้องการ domain จริงเพื่อออก SSL certificate)
- Git + SSH client

---

## Step 1: สร้าง Google Cloud VM

### 1.1 Login และตั้งค่า Project

```bash
# Login to Google Cloud
gcloud auth login

# ตั้งค่า Project
gcloud config set project YOUR_PROJECT_ID

# ตั้งค่า Region (แนะนำ asia-southeast1 สำหรับ Thailand)
gcloud config set compute/zone asia-southeast1-b
```

### 1.2 สร้าง VM Instance

```bash
gcloud compute instances create hai-nida-prod \
  --zone=asia-southeast1-b \
  --machine-type=e2-medium \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-balanced \
  --tags=http-server,https-server \
  --metadata=startup-script='#!/bin/bash
    apt-get update
    apt-get install -y docker.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker'
```

> **หมายเหตุ**: `e2-medium` (2 vCPU, 4GB RAM) เหมาะสำหรับเริ่มต้น หากมีผู้ใช้มากขึ้นแนะนำ `e2-standard-2` (2 vCPU, 8GB RAM) หรือสูงกว่า

### 1.3 ตั้งค่า Firewall Rules

```bash
# อนุญาต HTTP (Port 80)
gcloud compute firewall-rules create allow-http \
  --direction=INGRESS \
  --priority=1000 \
  --network=default \
  --action=ALLOW \
  --rules=tcp:80 \
  --target-tags=http-server \
  --source-ranges=0.0.0.0/0

# อนุญาต HTTPS (Port 443)
gcloud compute firewall-rules create allow-https \
  --direction=INGRESS \
  --priority=1000 \
  --network=default \
  --action=ALLOW \
  --rules=tcp:443 \
  --target-tags=https-server \
  --source-ranges=0.0.0.0/0

```

ไม่ต้องเปิด port 5000 ของ backend เพราะ frontend เรียก API ผ่าน Caddy ที่ path `/api` บน port 80/443 เดียวกับหน้าเว็บ ถ้าเคยสร้าง rule ไว้ให้ลบ
```bash
gcloud compute firewall-rules delete allow-backend-api
```

### 1.4 จอง Static IP

ถ้า VM มี external IP อยู่แล้ว ใช้สคริปต์ใน repo แปลง IP เดิมเป็น static ได้โดยไม่ต้องหยุดเครื่องและ IP ไม่เปลี่ยน
```bash
./scripts/gcp-static-ip.sh hai-nida-prod asia-southeast1-b
```

หรือสร้าง IP ใหม่แล้ว assign ให้ VM (IP จะเปลี่ยน)

```bash
# สร้าง Static IP
gcloud compute addresses create hai-nida-ip \
  --region=asia-southeast1

# ดู IP ที่ได้
gcloud compute addresses describe hai-nida-ip \
  --region=asia-southeast1 --format='get(address)'

# ลบ ephemeral IP เดิม
gcloud compute instances delete-access-config hai-nida-prod \
  --zone=asia-southeast1-b \
  --access-config-name="External NAT"

# Assign static IP ใหม่
gcloud compute instances add-access-config hai-nida-prod \
  --zone=asia-southeast1-b \
  --access-config-name="External NAT" \
  --address=YOUR_STATIC_IP
```


---

## Step 2: ติดตั้ง Docker และ Docker Compose

### 2.1 SSH เข้า VM

```bash
gcloud compute ssh hai-nida-prod --zone=asia-southeast1-b
```

### 2.2 ติดตั้ง Docker (หาก startup-script ยังไม่เสร็จ)

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine + Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add current user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

---

## Step 3: ตั้งค่า Google Gemini API Key

### 3.1 สร้าง API Key

```bash
# เปิด browser ไปที่ Google AI Studio
# https://aistudio.google.com/apikey
# คลิก "Create API Key" > เลือก Project > Copy key
```

### 3.2 (แนะนำ) เก็บ Key ใน Secret Manager

```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# สร้าง Secret
echo -n "YOUR_GEMINI_API_KEY" | \
  gcloud secrets create gemini-api-key \
  --replication-policy="automatic" \
  --data-file=-

# ดึง Secret (ใช้ตอน deploy)
gcloud secrets versions access latest --secret="gemini-api-key"
```

### 3.3 Gemini Model ที่รองรับ

| Model | ลักษณะ | แนะนำ |
|-------|--------|-------|
| `gemini-2.5-flash` | เร็ว, คุ้มค่า | ✅ Production |
| `gemini-2.5-pro` | ฉลาดกว่า, แพงกว่า | สำหรับงาน complex |
| `gemini-2.0-flash` | รุ่นก่อนหน้า | Fallback |

> **Rate Limits**: Free tier = 5 RPM / 25 RPD. Production ควรใช้ Paid tier (pay-as-you-go)
>
> ข้อมูลราคา: [Google AI Pricing](https://ai.google.dev/pricing)

---

## Step 4: ตั้งค่า DNS (ไม่บังคับ)

ถ้ายังไม่ใช้โดเมน ข้าม step นี้ได้ เข้าใช้งานผ่าน `http://<static IP>`

ตั้งค่า DNS A Record ที่ DNS provider ของคุณ:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | `your-domain.com` | `YOUR_VM_EXTERNAL_IP` | 300 |
| A | `www` | `YOUR_VM_EXTERNAL_IP` | 300 |

ตรวจสอบ DNS Propagation:

```bash
dig your-domain.com +short
nslookup your-domain.com
```

> DNS อาจใช้เวลา propagate 5-30 นาที (ขึ้นกับ TTL เดิม)


---

## Step 5: เตรียม Production Files

### 5.1 Clone Repository บน VM

```bash
# SSH เข้า VM
gcloud compute ssh hai-nida-prod --zone=asia-southeast1-b

# Clone repo
cd /opt
sudo mkdir -p hai-nida && sudo chown $USER:$USER hai-nida
git clone https://github.com/YOUR_USERNAME/Hai-Nida.git hai-nida
cd hai-nida
```

### 5.2 Caddyfile

ใช้ `Caddyfile` ที่อยู่ใน repo ไม่ต้องสร้างเอง ค่าเริ่มต้นรับ HTTP ที่ `:80` ผ่าน static IP

ถ้าจะใช้โดเมน ให้แก้บรรทัด `:80 {` เป็นชื่อโดเมน (เช่น `hai-nida.com {`) แล้ว commit เข้า repo Caddy จะออกใบรับรอง HTTPS จาก Let's Encrypt อัตโนมัติ อย่าแก้ไฟล์นี้บน VM โดยตรง เพราะการ deploy อัตโนมัติจะเขียนทับด้วยไฟล์จาก repo

### 5.3 สร้าง Production Environment File

```bash
cat > .env.prod << 'EOF'
# ===== Backend =====
GOOGLE_API_KEY=your-gemini-api-key-here
SECRET_KEY=generate-a-strong-random-key-here
ADMIN_EMAIL=admin@your-domain.com
ADMIN_USERNAME=admin@your-domain.com
ADMIN_PASSWORD=change-this-strong-password

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8000

# CORS - เว้นว่างได้ เพราะ frontend กับ backend อยู่ origin เดียวกัน
CORS_ORIGINS=
EOF
```

สร้าง SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5.4 Production docker-compose.prod.yml

ใช้ `docker-compose.prod.yml` ที่อยู่ใน repo มีเพียง Caddy ที่เปิด port `80`/`443` ออกภายนอก ส่วน frontend (80), backend (5000) และ chromadb (8000) ใช้ `expose` ภายใน Docker network

frontend ไม่ต้องรับ `REACT_APP_API_BASE_URL` ตอน build เพราะเรียก API ด้วย path relative (`/api/...`) ส่วน backend อ่านค่าจาก `.env.prod` ผ่าน `env_file` จึงไม่ต้อง export ตัวแปรก่อนสั่ง compose

---

## Step 6: Deploy ด้วย Docker Compose

### 6.1 Build และ Start

```bash
cd /opt/hai-nida

# Build และ start ทุก services (backend อ่าน .env.prod เอง)
docker compose -f docker-compose.prod.yml up --build -d
```

### 6.2 ตรวจสอบ Services

```bash
# ดู status
docker compose -f docker-compose.prod.yml ps

# ดู logs ทั้งหมด
docker compose -f docker-compose.prod.yml logs -f

# ดู logs เฉพาะ service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f caddy
```

### 6.3 ทดสอบ

```bash
# ทดสอบ Frontend และ Backend ผ่าน Caddy
curl -I http://localhost/
curl -I http://localhost/openapi.json

# ถ้าตั้งโดเมนแล้ว
curl -I http://your-domain.com    # ควร redirect 301 → https
curl -I https://your-domain.com   # ควรได้ 200
```

### 6.4 Initialize Database (ครั้งแรก)

```bash
docker compose -f docker-compose.prod.yml exec backend python init_db.py
```

---

## Step 7: ตรวจสอบและ Monitor

### 7.1 Health Check

```bash
docker compose -f docker-compose.prod.yml ps
docker stats
df -h
docker system df
```

### 7.2 ดู Logs

```bash
# Real-time
docker compose -f docker-compose.prod.yml logs -f --tail=100

# Caddy access logs
docker compose -f docker-compose.prod.yml exec caddy cat /data/access.log

# Backend errors
docker compose -f docker-compose.prod.yml logs backend --since="1h" | grep -i error
```

### 7.3 ตั้ง Google Cloud Monitoring (Optional)

```bash
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
sudo bash add-google-cloud-ops-agent-repo.sh --also-install
```


---

## Maintenance

### Update / Redeploy

push เข้า branch `main` แล้ว GitHub Actions จะ backup ChromaDB, ดึงโค้ด, build และ start ให้อัตโนมัติ ดู [DEPLOY_AUTOMATION.md](./DEPLOY_AUTOMATION.md)

ถ้าต้อง deploy เองบน VM
```bash
cd /opt/hai-nida
./backup-chromadb.sh
git pull origin main
docker compose -f docker-compose.prod.yml up --build -d
```

### Backup ChromaDB

ใช้สคริปต์ใน repo ไฟล์ backup เก็บที่ `/opt/hai-nida/backups/chromadb/` และเก็บไว้ 7 ชุดล่าสุด
```bash
./backup-chromadb.sh                # backup ทันที
./restore-chromadb.sh <ไฟล์ backup>  # restore
./setup-backup-cron.sh              # ตั้ง cron ให้ backup ทุกวัน
```

### Scale Up VM

```bash
gcloud compute instances stop hai-nida-prod --zone=asia-southeast1-b
gcloud compute instances set-machine-type hai-nida-prod \
  --zone=asia-southeast1-b --machine-type=e2-standard-2
gcloud compute instances start hai-nida-prod --zone=asia-southeast1-b
```

### SSL Certificate

ใช้เฉพาะเมื่อตั้งโดเมนแล้ว Caddy renew อัตโนมัติ ไม่ต้องทำอะไร ตรวจสอบ:
```bash
docker compose -f docker-compose.prod.yml exec caddy caddy list-certs
```

---

## Troubleshooting

### Container ไม่ Start

```bash
docker compose -f docker-compose.prod.yml logs --tail=50 SERVICE_NAME
docker ps -a --filter "status=exited"
docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml up -d
```

### Caddy ไม่ออก SSL Certificate

1. DNS ยังไม่ propagate → `dig your-domain.com +short`
2. Port 80/443 ถูก block → ตรวจ firewall rules
3. Domain ชี้ IP ผิด → แก้ DNS A record

### Backend เชื่อม ChromaDB ไม่ได้

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -c "import httpx; print(httpx.get('http://chromadb:8000/api/v1/heartbeat').json())"
```

### Gemini API Error

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -c "import os; print('Key set:', bool(os.environ.get('GOOGLE_API_KEY')))"
```

### Out of Memory

```bash
docker stats --no-stream

# เพิ่ม swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```


---

## Security Best Practices

1. **ห้าม commit** `.env.prod`, `backend/.env` หรือ API keys ลง Git (อยู่ใน `.gitignore` แล้ว ใช้ `backend/.env.example` เป็นแม่แบบ) และตั้ง `SECRET_KEY` ใน `.env.prod` เสมอ
2. ใช้ **Secret Manager** เก็บ production keys
3. เปิดเฉพาะ port 80, 443, 22 ไม่เปิด 5000 (Backend) และ 8000 (ChromaDB) ออก internet
4. การ deploy อัตโนมัติใช้ SSH key เฉพาะของ GitHub Actions จึงต้องปิด OS Login ที่ VM นี้ ส่วนการเข้าเครื่องด้วยตัวเองแนะนำ **IAP tunnel**:
   ```bash
   gcloud compute ssh hai-nida-prod --zone=asia-southeast1-b --tunnel-through-iap
   ```
5. frontend กับ backend อยู่ origin เดียวกัน ไม่ต้องพึ่ง CORS ถ้าต้องการจำกัดเพิ่ม ตั้ง `CORS_ORIGINS` เป็น URL ที่ผู้ใช้เข้าจริง
6. จำกัด Gemini API key: IP restriction + API restriction ใน Cloud Console
7. Update OS + Docker images สม่ำเสมอ

---

## Quick Reference

| Action | Command |
|--------|---------|
| SSH เข้า VM | `gcloud compute ssh hai-nida-prod --zone=asia-southeast1-b` |
| Start services | `docker compose -f docker-compose.prod.yml up -d` |
| Stop services | `docker compose -f docker-compose.prod.yml down` |
| View logs | `docker compose -f docker-compose.prod.yml logs -f` |
| Rebuild & deploy | `docker compose -f docker-compose.prod.yml up --build -d` |
| Container status | `docker compose -f docker-compose.prod.yml ps` |
| Restart service | `docker compose -f docker-compose.prod.yml restart backend` |
| Enter container | `docker compose -f docker-compose.prod.yml exec backend bash` |

---

## Cost Estimation

| Resource | Spec | Est. Monthly (USD) |
|----------|------|-------------------|
| Compute Engine (e2-medium) | 2 vCPU, 4GB RAM | ~$25-35 |
| Boot Disk (30GB) | pd-balanced | ~$3-5 |
| Static IP | 1 address | ~$3 |
| Network Egress | ~50GB/month | ~$5-8 |
| **Total** | | **~$36-51/month** |

> Gemini API: gemini-2.5-flash ~$0.15/1M input tokens, $0.60/1M output tokens
>
> [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator)

---

*Last updated: July 2026*
