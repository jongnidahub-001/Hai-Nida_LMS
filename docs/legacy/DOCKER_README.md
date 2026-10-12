# Docker Setup for Hai-Nida Project

This Docker setup containerizes all three services:
- **Frontend**: React app (port 3000)
- **Backend**: FastAPI app (port 5000)
- **Database**: ChromaDB (port 8000)

## Prerequisites

- Docker
- Docker Compose

## Quick Start

### 1. Build and Start All Services
```bash
docker-compose up --build
```

### 2. Start Services (after initial build)
```bash
docker-compose up
```

### 3. Start Services in Background
```bash
docker-compose up -d
```

### 4. Stop All Services
```bash
docker-compose down
```

### 5. Stop and Remove Volumes
```bash
docker-compose down -v
```

## Service Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **ChromaDB**: http://localhost:8000

## Development

### View Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs frontend
docker-compose logs backend
docker-compose logs chromadb
```

### Rebuild Specific Service
```bash
docker-compose build frontend
docker-compose build backend
```

### Enter Container Shell
```bash
docker-compose exec frontend sh
docker-compose exec backend bash
```

## Data Persistence

- ChromaDB data is persisted in `./chroma-data/` directory
- Backend temp files are mounted to `./backend/temp/`
- Backend ChromaDB files are mounted to `./backend/chroma_db/`

## Environment Variables

The services are configured to communicate with each other using Docker networking:
- Frontend connects to backend via `http://backend:5000` (internal)
- Backend connects to ChromaDB via `chromadb:8000` (internal)
- External access uses localhost ports

### Backend Environment Variables:
- `CHROMA_HOST=chromadb` - ChromaDB service hostname
- `CHROMA_PORT=8000` - ChromaDB service port

## Troubleshooting

### Port Conflicts
If ports 3000, 5000, or 8000 are already in use, modify the port mappings in `docker-compose.yml`:
```yaml
ports:
  - "3001:3000"  # Change external port
```

### Build Issues
Clear Docker cache and rebuild:
```bash
docker-compose down
docker system prune -a
docker-compose up --build
```

### Network Issues
Ensure all services are on the same network by checking:
```bash
docker network ls
docker network inspect hai-nida_app-network
```

### ChromaDB Connection Issues
If the backend cannot connect to ChromaDB:
1. Check that ChromaDB service is running:
   ```bash
   docker-compose ps chromadb
   ```
2. Verify environment variables are set correctly:
   ```bash
   docker-compose exec backend env | grep CHROMA
   ```
3. Test connectivity between services:
   ```bash
   docker-compose exec backend ping chromadb
   ```

The backend now uses `CHROMA_HOST=chromadb` instead of `localhost` to connect to ChromaDB. 