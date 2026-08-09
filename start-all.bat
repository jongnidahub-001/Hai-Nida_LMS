@echo off
cd /d "%~dp0"

echo === Starting Hai-Nida Development Environment ===
echo.

REM ===== Install Dependencies =====
echo [0/3] Installing dependencies...
echo.

REM Backend - create venv if not exists & install requirements
echo   → Backend: checking venv ^& installing packages...
cd backend
if not exist ".venv" (
    echo     Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt --quiet
call deactivate
cd ..

REM Frontend - npm install
echo   → Frontend: installing npm packages...
cd frontend
call npm install --silent
cd ..

echo.
echo   √ Dependencies installed
echo.

REM ===== Start Services =====

REM Terminal 1 - Chroma Database
echo [1/3] Starting ChromaDB...
start "Chroma" pwsh -NoExit -Command "cd backend; .\.venv\Scripts\activate; chroma run --host localhost --port 8000 --path ./chroma-data"

timeout /t 2 /nobreak >nul

REM Terminal 2 - Backend API Server
echo [2/3] Starting Backend API Server...
start "API Server" pwsh -NoExit -Command "cd backend; .\.venv\Scripts\activate; uvicorn app:app --host 0.0.0.0 --port 5000 --reload"

timeout /t 2 /nobreak >nul

REM Terminal 3 - Frontend
echo [3/3] Starting Frontend...
start "Frontend" pwsh -NoExit -Command "cd frontend; npm start"

echo.
echo === All services starting ===
echo.
echo   ChromaDB:  http://localhost:8000
echo   Backend:   http://localhost:5000
echo   Frontend:  http://localhost:3000
echo.
pause
