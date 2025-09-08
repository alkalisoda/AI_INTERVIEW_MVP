@echo off
echo Starting AI Interview System - Frontend and Backend...
echo.

REM 启动后端服务器
echo [1/2] Starting Backend Server...
start "AI Interview Backend" cmd /k "cd /d %~dp0backend && conda activate ai-interview && python main.py"

REM 等待2秒让后端先启动
timeout /t 2 /nobreak >nul

REM 启动前端开发服务器
echo [2/2] Starting Frontend Development Server...
start "AI Interview Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo AI Interview System Starting...
echo ========================================
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173 (or check frontend terminal)
echo API Docs: http://localhost:8000/docs
echo.
echo Both services are starting in separate windows.
echo Close this window or press any key to continue...
pause >nul
