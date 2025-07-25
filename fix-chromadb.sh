#!/bin/bash

echo "🔧 ChromaDB Docker Troubleshooting Script"
echo "=========================================="

# Stop any running containers
echo "1. Stopping existing containers..."
docker-compose down

# Create chroma_db directory with proper permissions if it doesn't exist
echo "2. Setting up chroma_db directory..."
if [ ! -d "./chroma_db" ]; then
    mkdir -p ./chroma_db
    echo "   ✅ Created chroma_db directory"
else
    echo "   ✅ chroma_db directory exists"
fi

# Fix permissions
echo "3. Fixing permissions..."
chmod 755 ./chroma_db
echo "   ✅ Set proper permissions on chroma_db"

# Clean up any orphaned containers
echo "4. Cleaning up..."
docker system prune -f
echo "   ✅ Cleaned up Docker system"

# Try to start ChromaDB alone first
echo "5. Testing ChromaDB service alone..."
docker-compose up chromadb --detach

# Wait a bit
sleep 10

# Check if ChromaDB is running
if docker-compose ps chromadb | grep -q "Up"; then
    echo "   ✅ ChromaDB is running successfully!"
    
    # Test the health endpoint
    echo "6. Testing ChromaDB health endpoint..."
    if curl -f http://localhost:8000/api/v1/heartbeat 2>/dev/null; then
        echo "   ✅ ChromaDB health check passed!"
    else
        echo "   ❌ ChromaDB health check failed"
    fi
else
    echo "   ❌ ChromaDB failed to start"
    echo "   📋 ChromaDB logs:"
    docker-compose logs chromadb
fi

echo ""
echo "🚀 Now you can start all services with:"
echo "   docker-compose up" 