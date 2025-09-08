@echo off
echo Starting AI Interview Backend...
echo.

REM 激活 conda 环境
call conda activate ai-interview

REM 检查 conda 环境是否激活成功
if %errorlevel% neq 0 (
    echo Error: Failed to activate conda environment 'ai-interview'
    echo Please make sure the environment exists: conda env list
    pause
    exit /b 1
)

echo Conda environment 'ai-interview' activated successfully
echo.

REM 切换到后端目录
cd /d "%~dp0backend"

REM 检查是否在正确的目录
if not exist "main.py" (
    echo Error: main.py not found in backend directory
    echo Current directory: %cd%
    pause
    exit /b 1
)

echo Starting FastAPI server...
echo Backend will be available at: http://localhost:8000
echo API documentation at: http://localhost:8000/docs
echo.

REM 启动后端服务器
python main.py

REM 如果服务器退出，保持窗口打开
if %errorlevel% neq 0 (
    echo.
    echo Backend exited with error code: %errorlevel%
    pause
)


