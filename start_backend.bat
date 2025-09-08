@echo off
echo Starting AI Interview Backend...
echo.

REM Activate conda environment
call conda activate ai-interview

REM Check if conda environment activation was successful
if %errorlevel% neq 0 (
    echo Error: Failed to activate conda environment 'ai-interview'
    echo Please make sure the environment exists: conda env list
    pause
    exit /b 1
)

echo Conda environment 'ai-interview' activated successfully
echo.

REM Switch to backend directory
cd /d "%~dp0backend"

REM Check if in correct directory
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

REM Start backend server
python main.py

REM If server exits, keep window open
if %errorlevel% neq 0 (
    echo.
    echo Backend exited with error code: %errorlevel%
    pause
)


