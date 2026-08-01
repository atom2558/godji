@echo off
title AI Godji Master One-Click Launcher
echo =========================================================
echo   🐉 AI Godji Master One-Click Launcher
echo =========================================================
echo.

:: 1. Auto-kill any old ghost server process running on Port 8000
echo [1/4] Clearing old background processes on Port 8000...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :8000') do (
    taskkill /f /pid %%a >nul 2>&1
)

:: 2. Start Ollama local AI service in background
echo [2/4] Starting Local Ollama AI Engine...
start /b ollama serve >nul 2>&1

:: 3. Start Python Backend Server on Port 8000
echo [3/4] Starting Fresh Python Backend Server (Port 8000)...
cd /d "D:\godji\aigodij\backend"
start "AI Godji Server" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: 4. Brief pause for backend startup
timeout /t 3 /nobreak >nul

:: 5. Start Electron Desktop Application
echo [4/4] Launching AI Godji Electron Desktop Application...
cd /d "D:\godji\aigodij\frontend"
start "AI Godji Desktop" cmd /c "npm start"

echo.
echo =========================================================
echo   🚀 AI Godji All-In-One Environment Launching!
echo =========================================================
exit
