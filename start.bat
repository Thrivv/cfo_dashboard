@echo off
echo Starting CFO Dashboard with Docker...

REM Check if Docker is running
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker is not installed or not running
    echo Please install Docker Desktop and start it
    pause
    exit /b 1
)

REM Build and start containers
echo Building Docker image...
docker build -t cfo-dashboard .

echo Starting containers...
docker-compose up -d

echo CFO Dashboard is starting...
echo Access at: http://localhost
echo Direct access: http://localhost:8501

pause