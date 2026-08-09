# Deployment Guide (Web Console Version) - Hai-Nida LMS

คู่มือการ Deploy ระบบ Hai-Nida LMS บน Google Cloud Platform ผ่าน **Google Cloud Console (Web UI)**

> 📌 ดูเวอร์ชัน CLI ได้ที่ [DEPLOYMENT_GUIDE_CLI.md](./DEPLOYMENT_GUIDE_CLI.md)

## สารบัญ

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Step 1: สร้าง Google Cloud VM](#step-1-สร้าง-google-cloud-vm)
- [Step 2: ติดตั้ง Docker และ Docker Compose](#step-2-ติดตั้ง-docker-และ-docker-compose)
- [Step 3: ตั้งค่า Google Gemini API Key](#step-3-ตั้งค่า-google-gemini-api-key)
- [Step 4: ตั้งค่า DNS](#step-4-ตั้งค่า-dns)
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
         │  │internal│ │5000)   │  │
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
- Google Gemini API Key จาก [Google AI Studio](https://aistudio.google.com/apikey)
- Domain name ที่จัดการ DNS records ได้
- Web browser (สำหรับ Google Cloud Console)

---

## Step 1: สร้าง Google Cloud VM

### 1.1 เข้า Google Cloud Console

1. เปิด [https://console.cloud.google.com](https://console.cloud.google.com)
2. เลือก Project ที่ต้องการ (หรือสร้างใหม่)

### 1.2 สร้าง VM Instance

1. ไปที่ **Compute Engine** > **VM instances**
2. คลิก **"Create Instance"**
3. กรอกข้อมูล:

| Field | Value |
|-------|-------|
| Name | `hai-nida-prod` |
| Region | `asia-southeast1 (Singapore)` |
| Zone | `asia-southeast1-b` |
| Machine type | `e2-medium` (2 vCPU, 4GB RAM) |
| Boot disk | Ubuntu 24.04 LTS, 30GB, Balanced persistent disk |
| Firewall | ✅ Allow HTTP traffic, ✅ Allow HTTPS traffic |

4. คลิก **"Advanced options"** > **"Management"**
5. ใน **"Automation > Startup script"** ใส่:

```bash
#!/bin/bash
apt-get update
apt-get install -y docker.io docker-compose-plugin
systemctl enable docker
systemctl start docker
```

6. คลิก **"Create"**

> **หมายเหตุ**: `e2-medium` เหมาะสำหรับเริ่มต้น หากมีผู้ใช้มากแนะนำ `e2-standard-2` (8GB RAM)

### 1.3 ตั้งค่า Firewall Rules (ตรวจสอบ)

1. ไปที่ **VPC Network** > **Firewall**
2. ตรวจสอบว่ามี rules เหล่านี้ (สร้างอัตโนมัติจาก checkbox):
   - `default-allow-http` — TCP:80, source 0.0.0.0/0, target tag: http-server
   - `default-allow-https` — TCP:443, source 0.0.0.0/0, target tag: https-server

หากไม่มี ให้สร้างใหม่:
1. คลิก **"Create Firewall Rule"**
2. กรอก:
   - Name: `allow-http`
   - Direction: Ingress
   - Targets: Specified target tags → `http-server`
   - Source IP ranges: `0.0.0.0/0`
   - Protocols and ports: TCP → `80`
3. คลิก **"Create"**
4. ทำซ้ำสำหรับ HTTPS (port `443`, tag `https-server`)

**สร้าง Firewall Rule สำหรับ Backend API (Port 5000):**

1. คลิก **"Create Firewall Rule"**
2. กรอก:
   - Name: `allow-backend-api`
   - Direction: Ingress
   - Targets: Specified target tags → `http-server`
   - Source IP ranges: `0.0.0.0/0`
   - Protocols and ports: TCP → `5000`
3. คลิก **"Create"**

> **หมายเหตุ**: Port 5000 จำเป็นเพราะ Frontend (React) เรียก Backend API โดยตรงจาก browser ของ user ผ่าน `REACT_APP_API_BASE_URL`

### 1.4 จอง Static IP (แนะนำ)

1. ไปที่ **VPC Network** > **IP addresses**
2. คลิก **"Reserve External Static Address"**
3. กรอก:
   - Name: `hai-nida-ip`
   - Network tier: Premium
   - IP version: IPv4
   - Type: Regional
   - Region: `asia-southeast1`
   - Attached to: `hai-nida-prod`
4. คลิก **"Reserve"**

> IP address ที่ได้จะแสดงในหน้า — จดไว้ใช้ตั้ง DNS


---

## Step 2: ติดตั้ง Docker และ Docker Compose

### 2.1 SSH เข้า VM ผ่าน Web Console

1. ไปที่ **Compute Engine** > **VM instances**
2. คลิกปุ่ม **"SSH"** ที่แถวของ `hai-nida-prod`
3. จะเปิดหน้าต่าง terminal ใน browser

### 2.2 ตรวจสอบ Docker (startup-script ติดตั้งให้แล้ว)

```bash
# ตรวจสอบว่า Docker ติดตั้งแล้ว
docker --version
docker compose version
```

หากยังไม่มี (startup-script ยังไม่เสร็จ) ให้ติดตั้งเอง:

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
sudo apt-get install -y ca-certificates curl gnupg lsb-release

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

---

## Step 3: ตั้งค่า Google Gemini API Key

### 3.1 สร้าง API Key ผ่าน Google AI Studio

1. เปิด [Google AI Studio](https://aistudio.google.com/apikey)
2. คลิก **"Create API Key"**
3. เลือก Google Cloud Project
4. คลิก **"Create API key in existing project"**
5. Copy API Key เก็บไว้

### 3.2 (แนะนำ) เก็บ Key ใน Secret Manager ผ่าน Web

1. ไปที่ [Secret Manager](https://console.cloud.google.com/security/secret-manager) ใน Cloud Console
2. คลิก **"Create Secret"**
3. กรอก:
   - Name: `gemini-api-key`
   - Secret value: วาง API Key ที่ copy มา
4. คลิก **"Create Secret"**

เมื่อต้องการดึง key มาใช้ (ใน SSH terminal):
```bash
gcloud secrets versions access latest --secret="gemini-api-key"
```

### 3.3 Gemini Model ที่รองรับ

| Model | ลักษณะ | แนะนำ |
|-------|--------|-------|
| `gemini-2.5-flash` | เร็ว, คุ้มค่า | ✅ Production |
| `gemini-2.5-pro` | ฉลาดกว่า, แพงกว่า | สำหรับงาน complex |
| `gemini-2.0-flash` | รุ่นก่อนหน้า | Fallback |

> **Rate Limits**: Free tier = 5 RPM / 25 RPD. Production ควรใช้ Paid tier
>
> ข้อมูลราคา: [Google AI Pricing](https://ai.google.dev/pricing)


---

## Step 4: ตั้งค่า DNS

### 4.1 ดู External IP ของ VM

1. ไปที่ **Compute Engine** > **VM instances**
2. ดู column **"External IP"** ของ `hai-nida-prod`
3. จดค่า IP (เช่น `34.87.xxx.xxx`)

### 4.2 ตั้ง DNS A Record

ไปที่ DNS provider ของคุณ (เช่น Cloudflare, GoDaddy, Namecheap, etc.) แล้วเพิ่ม:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | `@` (หรือ domain หลัก) | `YOUR_VM_EXTERNAL_IP` | 300 |
| A | `www` | `YOUR_VM_EXTERNAL_IP` | 300 |

### 4.3 (Optional) ใช้ Google Cloud DNS

1. ไปที่ **Network services** > **Cloud DNS**
2. คลิก **"Create zone"**
3. กรอก Zone name และ DNS name (domain ของคุณ)
4. คลิก **"Create"**
5. เพิ่ม **Record set**:
   - Type: `A`
   - IPv4 Address: IP ของ VM
   - TTL: `300`
6. อัพเดต nameserver ที่ domain registrar ให้ชี้มาที่ Google Cloud DNS

### 4.4 ตรวจสอบ DNS (ใน SSH terminal)

```bash
dig your-domain.com +short
nslookup your-domain.com
```

> DNS อาจใช้เวลา propagate 5-30 นาที

---

## Step 5: เตรียม Production Files

### 5.1 SSH เข้า VM และ Clone Repository

กดปุ่ม **"SSH"** ที่ VM instances แล้วรัน:

```bash
cd /opt
sudo mkdir -p hai-nida && sudo chown $USER:$USER hai-nida
git clone https://github.com/YOUR_USERNAME/Hai-Nida.git hai-nida
cd hai-nida
```

### 5.2 สร้าง Caddyfile

```bash
cat > Caddyfile << 'EOF'
your-domain.com {
    # Backend API - ต้องอยู่ก่อน frontend (more specific path)
    handle /api/* {
        reverse_proxy backend:5000
    }

    handle /docs {
        reverse_proxy backend:5000
    }

    handle /openapi.json {
        reverse_proxy backend:5000
    }

    handle /redoc {
        reverse_proxy backend:5000
    }

    # Frontend - React SPA (catch-all)
    handle {
        reverse_proxy frontend:80
    }

    # Logging
    log {
        output file /data/access.log {
            roll_size 10mb
            roll_keep 5
        }
    }
}
EOF
```

> **สำคัญ**: แทนที่ `your-domain.com` ด้วย domain จริง

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

# CORS - domain จริง
CORS_ORIGINS=https://your-domain.com

# ===== Frontend =====
REACT_APP_API_BASE_URL=https://your-domain.com
EOF
```

สร้าง SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```


### 5.4 Production docker-compose.prod.yml

```yaml
version: '3.8'

services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - frontend
      - backend
    networks:
      - app-network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
      args:
        - REACT_APP_API_BASE_URL=${REACT_APP_API_BASE_URL}
    expose:
      - "80"
    depends_on:
      - backend
    networks:
      - app-network
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    environment:
      - CHROMA_HOST=${CHROMA_HOST:-chromadb}
      - CHROMA_PORT=${CHROMA_PORT:-8000}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS}
    depends_on:
      - chromadb
    volumes:
      - ./backend/temp:/app/temp
      - ./backend/chroma_db:/app/chroma_db
    networks:
      - app-network
    restart: unless-stopped

  chromadb:
    image: chromadb/chroma:1.0.15
    expose:
      - "8000"
    volumes:
      - chroma-data:/chroma/chroma
    environment:
      - CHROMA_DB_IMPL=chromadb.db.impl.sqlite.SqliteDB
    networks:
      - app-network
    restart: unless-stopped

networks:
  app-network:
    driver: bridge

volumes:
  caddy_data:
  caddy_config:
  chroma-data:
```

> Backend ใช้ `ports: "5000:5000"` เพราะ React frontend เรียก API ตรงจาก browser ของ user ส่วน ChromaDB ใช้ `expose` เพราะถูกเรียกจาก backend ภายใน Docker network เท่านั้น

---

## Step 6: Deploy ด้วย Docker Compose

ใน SSH terminal ของ VM:

### 6.1 Build และ Start

```bash
cd /opt/hai-nida

# Load environment variables
export $(cat .env.prod | grep -v '^#' | xargs)

# Build และ start
docker compose -f docker-compose.prod.yml up --build -d
```

### 6.2 ตรวจสอบ Services

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

### 6.3 ทดสอบ

```bash
# ทดสอบจาก VM
curl -I http://your-domain.com
curl -I https://your-domain.com
curl https://your-domain.com/api/health
```

หรือเปิด browser แล้วเข้า `https://your-domain.com`

### 6.4 Initialize Database (ครั้งแรก)

```bash
docker compose -f docker-compose.prod.yml exec backend python init_db.py
```


---

## Step 7: ตรวจสอบและ Monitor

### 7.1 ดูผ่าน Cloud Console

1. **VM Status**: Compute Engine > VM instances → ดูสถานะ (running ✅)
2. **CPU/Memory**: คลิกที่ VM → tab **"Monitoring"** → ดู CPU, Memory, Disk
3. **Serial Port Logs**: คลิก VM → tab **"Serial port 1 (console)"** → ดู boot logs

### 7.2 ดูผ่าน SSH Terminal

```bash
# Container status
docker compose -f docker-compose.prod.yml ps

# Resource usage
docker stats

# Real-time logs
docker compose -f docker-compose.prod.yml logs -f --tail=100

# Backend errors
docker compose -f docker-compose.prod.yml logs backend --since="1h" | grep -i error
```

### 7.3 ตั้ง Google Cloud Monitoring (Optional)

1. ไปที่ [Cloud Monitoring](https://console.cloud.google.com/monitoring)
2. คลิก **"Install Ops Agent"** สำหรับ VM ที่ต้องการ
3. หรือติดตั้งผ่าน SSH:

```bash
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
sudo bash add-google-cloud-ops-agent-repo.sh --also-install
```

4. ดู Metrics/Dashboards ได้ที่ Cloud Console > Monitoring

### 7.4 ตั้ง Uptime Check (Optional)

1. ไปที่ **Monitoring** > **Uptime checks**
2. คลิก **"Create Uptime Check"**
3. กรอก:
   - Protocol: HTTPS
   - Hostname: `your-domain.com`
   - Path: `/api/health`
   - Check frequency: 5 minutes
4. ตั้ง Alert ให้แจ้งเตือนทาง Email เมื่อ site ล่ม

---

## Maintenance

### Update / Redeploy

SSH เข้า VM แล้วรัน:
```bash
cd /opt/hai-nida
git pull origin main
docker compose -f docker-compose.prod.yml up --build -d
```

### Backup ChromaDB

```bash
cat > /opt/hai-nida/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/hai-nida/backups"
mkdir -p $BACKUP_DIR
docker compose -f /opt/hai-nida/docker-compose.prod.yml exec -T chromadb \
  tar -czf - /chroma/chroma > $BACKUP_DIR/chroma-$(date +%Y%m%d-%H%M).tar.gz
find $BACKUP_DIR -name "chroma-*.tar.gz" -mtime +7 -delete
echo "Backup completed: $(date)"
EOF
chmod +x /opt/hai-nida/backup.sh

# ตั้ง cron - backup ทุกวัน 3:00 AM
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/hai-nida/backup.sh >> /var/log/hai-nida-backup.log 2>&1") | crontab -
```

### Scale Up VM ผ่าน Web Console

1. ไปที่ **Compute Engine** > **VM instances**
2. **Stop** VM (คลิก ⋮ > Stop)
3. คลิกชื่อ VM > **"Edit"**
4. เปลี่ยน Machine type เป็น `e2-standard-2` (หรือขนาดที่ต้องการ)
5. คลิก **"Save"**
6. **Start** VM กลับ

### Increase Disk Size ผ่าน Web Console

1. ไปที่ **Compute Engine** > **Disks**
2. คลิก disk ของ VM
3. คลิก **"Edit"** > เพิ่ม Size
4. คลิก **"Save"**
5. SSH เข้า VM แล้วรัน:
```bash
sudo resize2fs /dev/sda1
```

### SSL Certificate

Caddy renew อัตโนมัติ ไม่ต้องทำอะไร


---

## Troubleshooting

### Container ไม่ Start

SSH เข้า VM แล้วรัน:
```bash
docker compose -f docker-compose.prod.yml logs --tail=50 SERVICE_NAME
docker ps -a --filter "status=exited"
docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml up -d
```

### Caddy ไม่ออก SSL Certificate

1. **DNS ยังไม่ propagate** → รอ 5-30 นาที
2. **Port 80/443 ถูก block** → ตรวจ Firewall:
   - Cloud Console > VPC Network > Firewall
   - ตรวจว่ามี allow-http และ allow-https
3. **Domain ชี้ IP ผิด** → ตรวจ DNS A record

```bash
# ตรวจจาก VM
docker compose -f docker-compose.prod.yml logs caddy
dig your-domain.com +short
```

### Backend เชื่อม ChromaDB ไม่ได้

```bash
docker compose -f docker-compose.prod.yml ps chromadb
docker compose -f docker-compose.prod.yml exec backend \
  python -c "import httpx; print(httpx.get('http://chromadb:8000/api/v1/heartbeat').json())"
```

### Gemini API Error

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -c "import os; print('Key set:', bool(os.environ.get('GOOGLE_API_KEY')))"
```

ตรวจสอบ API key ใน Cloud Console:
1. ไปที่ **APIs & Services** > **Credentials**
2. ตรวจว่า key ยัง active และไม่ถูก restrict ผิด

### Out of Memory

ดูใน Cloud Console: VM instances > คลิก VM > Monitoring tab > Memory

หรือ SSH:
```bash
docker stats --no-stream
free -h
```

เพิ่ม swap:
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### VM ไม่สามารถเข้าถึงจากภายนอก

ตรวจสอบผ่าน Cloud Console:
1. **VM status** = Running ✅
2. **External IP** มีค่า (ไม่ใช่ None)
3. **Firewall rules** เปิด port 80, 443
4. **Network tags** ของ VM มี `http-server`, `https-server`


---

## Security Best Practices

### 1. Gemini API Key Security

ตั้งค่า restrictions ผ่าน Cloud Console:
1. ไปที่ **APIs & Services** > **Credentials**
2. คลิก API key ที่ใช้
3. ตั้ง **Application restrictions**:
   - เลือก "IP addresses"
   - เพิ่ม IP ของ VM
4. ตั้ง **API restrictions**:
   - เลือก "Restrict key"
   - เลือก "Generative Language API"
5. คลิก **"Save"**

### 2. Firewall (ตรวจสอบผ่าน Console)

ไปที่ **VPC Network** > **Firewall** ตรวจว่า:
- ✅ เปิด port 80, 443 (HTTP/HTTPS)
- ✅ เปิด port 5000 (Backend API — React frontend เรียกตรงจาก browser)
- ✅ เปิด port 22 (SSH) — default มีอยู่แล้ว
- ❌ **ไม่เปิด** port 8000 (ChromaDB) ออก internet

### 3. Environment Variables

- **ห้าม** commit `.env.prod` ลง Git
- ใช้ Secret Manager เก็บ sensitive data
- เปลี่ยน default admin password ทันทีหลัง deploy

### 4. CORS

ตั้ง `CORS_ORIGINS=https://your-domain.com` (domain จริงเท่านั้น ไม่ใช่ `*`)

### 5. SSH Access

แนะนำใช้ **OS Login** หรือ **IAP Tunnel** แทน SSH key ปกติ:
1. ไปที่ **Compute Engine** > **Settings** > **Metadata**
2. เพิ่ม `enable-oslogin` = `TRUE`

### 6. Regular Updates (SSH terminal)

```bash
sudo apt-get update && sudo apt-get upgrade -y
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## Quick Reference

### Web Console URLs

| Page | URL |
|------|-----|
| VM Instances | https://console.cloud.google.com/compute/instances |
| Firewall Rules | https://console.cloud.google.com/networking/firewalls |
| IP Addresses | https://console.cloud.google.com/networking/addresses |
| Secret Manager | https://console.cloud.google.com/security/secret-manager |
| Monitoring | https://console.cloud.google.com/monitoring |
| APIs & Services | https://console.cloud.google.com/apis/credentials |
| Cloud DNS | https://console.cloud.google.com/net-services/dns |

### SSH Commands ที่ใช้บ่อย

| Action | Command |
|--------|---------|
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
