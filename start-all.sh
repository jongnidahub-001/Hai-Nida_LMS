#!/bin/bash
cd "$(dirname "$0")"

echo "=== Starting Hai-Nida Development Environment ==="
echo ""

# ===== Install Dependencies =====
echo "[0/3] Installing dependencies..."
echo ""

# Backend - create venv if not exists & install requirements
echo "  → Backend: checking venv & installing packages..."
cd backend
if [ ! -d ".venv" ]; then
  echo "    Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt --quiet
deactivate
cd ..

# Frontend - npm install
echo "  → Frontend: installing npm packages..."
cd frontend
npm install --silent
cd ..

echo ""
echo "  ✓ Dependencies installed"
echo ""

# ===== Start Services =====

# Terminal 1 - ChromaDB
echo "[1/3] Starting ChromaDB..."
osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'/backend && source .venv/bin/activate && chroma run --host localhost --port 8000 --path ./chroma-data"' 2>/dev/null \
  || (cd backend && source .venv/bin/activate && chroma run --host localhost --port 8000 --path ./chroma-data &)

sleep 2

# Terminal 2 - Backend API Server
echo "[2/3] Starting Backend API Server..."
osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'/backend && source .venv/bin/activate && uvicorn app:app --host 0.0.0.0 --port 5000 --reload"' 2>/dev/null \
  || (cd backend && source .venv/bin/activate && uvicorn app:app --host 0.0.0.0 --port 5000 --reload &)

sleep 2

# Terminal 3 - Frontend
echo "[3/3] Starting Frontend..."
osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'/frontend && npm start"' 2>/dev/null \
  || (cd frontend && npm start &)

echo ""
echo "=== All services starting ==="
echo ""
echo "  ChromaDB:  http://localhost:8000"
echo "  Backend:   http://localhost:5000"
echo "  Frontend:  http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop background processes (if not using separate terminals)"
wait
