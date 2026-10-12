# Docker Setup Guide

This Docker Compose configuration sets up your complete learning management system with React frontend, FastAPI backend, and ChromaDB.

## Services

- **ChromaDB**: Vector database running on port 8000
- **FastAPI Backend**: Python API server running on port 5000  
- **React Frontend**: Web application running on port 3000

## Quick Start

1. **Build and start all services:**
   ```bash
   docker-compose up --build
   ```

2. **Start services in detached mode:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   # All services
   docker-compose logs
   
   # Specific service
   docker-compose logs frontend
   docker-compose logs backend
   docker-compose logs chromadb
   ```

4. **Stop all services:**
   ```bash
   docker-compose down
   ```

5. **Stop and remove volumes:**
   ```bash
   docker-compose down -v
   ```

## Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **ChromaDB**: http://localhost:8000

## Development

The setup includes volume mounts for live development:

- Frontend code changes will trigger automatic reloads
- Backend code changes will be reflected (you may need to restart the backend service)
- ChromaDB data is persisted in the `./chroma_db` directory

## Rebuilding Services

If you make changes to dependencies:

```bash
# Rebuild specific service
docker-compose build backend
docker-compose build frontend

# Rebuild all services
docker-compose build --no-cache
```

## Troubleshooting

### ChromaDB Issues

If ChromaDB fails to start:

1. **Run the fix script**:
   ```bash
   chmod +x fix-chromadb.sh
   ./fix-chromadb.sh
   ```

2. **Manual steps**:
   ```bash
   # Stop all services
   docker-compose down
   
   # Create directory with proper permissions
   mkdir -p ./chroma_db
   chmod 755 ./chroma_db
   
   # Test ChromaDB alone
   docker-compose up chromadb
   ```

3. **Check ChromaDB logs**:
   ```bash
   docker-compose logs chromadb
   ```

4. **Alternative ChromaDB configuration** (if still failing):
   Replace the chromadb service in docker-compose.yml with:
   ```yaml
   chromadb:
     image: chromadb/chroma:latest
     container_name: chromadb
     ports:
       - "8000:8000"
     volumes:
       - ./chroma_db:/chroma_db
     command: ["chroma", "run", "--host", "0.0.0.0", "--port", "8000", "--path", "/chroma_db"]
     networks:
       - app-network
   ```

### Other Issues

1. **Port conflicts**: Ensure ports 3000, 5000, and 8000 are available
2. **ChromaDB not ready**: The backend waits for ChromaDB health check to pass
3. **Permission issues**: Ensure the `chroma_db` directory has proper permissions
4. **Backend dependency issues**: Rebuild backend if requirements change

## Health Checks

All services include health checks:
- ChromaDB: Checks API heartbeat
- Backend: Checks API hello endpoint  
- Frontend: Checks web server availability 