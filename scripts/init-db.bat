@echo off
REM Database initialization script for Image Rating Server (Windows)

setlocal enabledelayedexpansion

echo ============================================
echo Database Initialization
echo ============================================
echo.

REM Change to backend directory
cd /d "%~dp0..\backend"

REM Run database initialization
echo Initializing database...
uv run python -m app.db.init_db

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo Database initialized successfully!
    echo ============================================
    echo.
    echo Default user created:
    echo   Email:    demo@example.com
    echo   Password: password123
    echo.
) else (
    echo.
    echo [ERROR] Database initialization failed!
    exit /b 1
)

endlocal
