# Production Deployment Guide

> เอกสารนี้เป็นแนวทางเดิม การ deploy production ปัจจุบันดู [DEPLOYMENT_GUIDE_WEB.md](./DEPLOYMENT_GUIDE_WEB.md) และ [DEPLOY_AUTOMATION.md](./DEPLOY_AUTOMATION.md) frontend ไม่ต้องตั้ง `REACT_APP_API_BASE_URL` แล้ว

## Quick Start

Choose the deployment scenario that fits your needs:

### 1. Local Production (All services on same server)
```bash
# Build and run everything in production mode
docker-compose -f docker-compose.prod.yml up --build -d

# Access your application:
# Frontend: http://localhost
# Backend API: http://localhost:5000
# ChromaDB: http://localhost:8000
```

### 2. External Production (Different servers/domains)
```bash
# 1. Update the API URL in docker-compose.external.yml
# 2. Replace 'https://your-backend-domain.com' with your actual backend URL
# 3. Build and run:
docker-compose -f docker-compose.external.yml up --build -d
```

### 3. Cloud Production (AWS, GCP, Azure, etc.)
```bash
# 1. Set your production API URL as an environment variable
export REACT_APP_API_BASE_URL=https://your-api.your-domain.com

# 2. Build with the environment variable
docker build -f frontend/Dockerfile.prod \
  --build-arg REACT_APP_API_BASE_URL=$REACT_APP_API_BASE_URL \
  -t your-app-frontend ./frontend

# 3. Push to your container registry and deploy
```

## Files Overview

- `docker-compose.prod.yml` - Production setup for all services on same server
- `docker-compose.external.yml` - Production setup for external API
- `frontend/Dockerfile.prod` - Production frontend build with nginx
- `docker-compose.yml` - Development setup (original)

## Production Features

✅ **Optimized React Build**: Uses `npm run build` for smaller, faster app  
✅ **Nginx Web Server**: Serves static files efficiently  
✅ **Auto Restart**: Containers restart automatically if they crash  
✅ **Environment Variables**: Proper API URL configuration  
✅ **Multi-stage Build**: Smaller final image size  

## SSL/HTTPS Setup

For production, you'll want to add SSL. You can:

1. **Use a reverse proxy** (nginx, Traefik, Cloudflare)
2. **Add SSL to docker-compose** with Let's Encrypt
3. **Deploy behind a load balancer** (AWS ALB, Google Cloud Load Balancer)

## Monitoring

Consider adding:
- Health checks to docker-compose
- Logging configuration
- Resource limits
- Monitoring tools (Prometheus, Grafana)

## Rollback

To switch back to development:
```bash
docker-compose down
docker-compose up
``` 