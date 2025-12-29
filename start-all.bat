@echo off
cd /d "%~dp0"

REM Terminal 1 - Chroma Database (backend + venv)
start "Chroma" pwsh -NoExit -Command "cd backend; .\.venv\Scripts\activate; chroma run --host localhost --port 8000 --path ./chroma-data"

REM Terminal 2 - Backend API Server
start "API Server" pwsh -NoExit -Command "cd backend; .\.venv\Scripts\activate; uvicorn app:app --host 0.0.0.0 --port 5000 --reload"

REM Terminal 3 - Frontend
start "Frontend" pwsh -NoExit -Command "cd frontend; npm start"

