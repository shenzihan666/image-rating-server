@echo off
REM Development startup script for Image Rating Server (Windows)
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_DIR=%%~fI"

echo ============================================
echo Starting Image Rating Server Development
echo ============================================
echo Project directory: %PROJECT_DIR%
echo.

where uv >nul 2>nul
if errorlevel 1 (
    echo [ERROR] uv is not installed.
    echo Install guide: https://docs.astral.sh/uv/getting-started/installation/
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm is not installed or not in PATH.
    exit /b 1
)

echo Installing backend dependencies with uv...
cd /d "%PROJECT_DIR%\backend"
call uv sync
if errorlevel 1 (
    echo [ERROR] Failed to install backend dependencies.
    exit /b 1
)

if not exist "%PROJECT_DIR%\frontend\node_modules" (
    echo Installing frontend dependencies...
    cd /d "%PROJECT_DIR%\frontend"
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies.
        exit /b 1
    )
)

if not exist "%PROJECT_DIR%\backend\logs" mkdir "%PROJECT_DIR%\backend\logs"

echo.
echo Starting backend server on port 8080...
start "Image Rating Backend" cmd /k "cd /d ""%PROJECT_DIR%\backend"" && uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload"

timeout /t 2 /nobreak >nul

echo Starting frontend server on port 8081...
start "Image Rating Frontend" cmd /k "cd /d ""%PROJECT_DIR%\frontend"" && npm run dev"

echo.
echo ============================================
echo Development servers are running!
echo ============================================
echo Backend API: http://localhost:8080
echo API Docs:    http://localhost:8080/docs
echo Frontend:    http://localhost:8081
echo.
echo Services are running in separate windows.
echo Close those windows to stop the servers.

endlocal
