@echo off

REM Move to the folder where this script is located
cd /d "%~dp0"

echo Starting Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

echo Waiting for Docker to start...
timeout /t 20 /nobreak >nul

echo Running docker compose...
start "Moodle App" cmd /k "cd /d %~dp0 && docker compose up"

echo Waiting for Streamlit to be ready...
timeout /t 20 /nobreak >nul

echo Opening browser...
start http://localhost:8501