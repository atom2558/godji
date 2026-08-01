@echo off
title Launching AI Godji...
echo ===========================================
echo 🐉 Starting AI Godji Desktop Assistant...
echo ===========================================
cd /d "%~dp0frontend"
cmd /c npm start
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️ An error occurred while running AI Godji.
    pause
)
