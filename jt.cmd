@echo off
setlocal enabledelayedexpansion

rem ============================================================================
rem Job Tracker (jt.cmd) - Windows CLI Launcher
rem Supports Command Prompt and PowerShell
rem ============================================================================

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

set "COMMAND=%~1"
if "%COMMAND%"=="" set "COMMAND=start"

rem ============================================================================
rem Route Subcommands
rem ============================================================================
if /i "%COMMAND%"=="start" goto handle_start
if /i "%COMMAND%"=="up" goto handle_start
if /i "%COMMAND%"=="dev" goto handle_dev
if /i "%COMMAND%"=="stop" goto handle_stop
if /i "%COMMAND%"=="down" goto handle_stop
if /i "%COMMAND%"=="status" goto handle_status
if /i "%COMMAND%"=="ps" goto handle_status
if /i "%COMMAND%"=="logs" goto handle_logs
if /i "%COMMAND%"=="open" goto handle_open
if /i "%COMMAND%"=="update" goto handle_update
if /i "%COMMAND%"=="reset" goto handle_reset
if /i "%COMMAND%"=="seed" goto handle_seed
if /i "%COMMAND%"=="help" goto handle_help
if /i "%COMMAND%"=="-h" goto handle_help
if /i "%COMMAND%"=="--help" goto handle_help
if /i "%COMMAND%"=="/?" goto handle_help
if /i "%COMMAND%"=="-?" goto handle_help

goto handle_unknown

rem ============================================================================
rem Helper: Ensure .env exists
rem ============================================================================
:ensure_env
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating initial .env configuration from .env.example...
        copy .env.example .env >nul
    )
)
exit /b 0

rem ============================================================================
rem Command Handlers
rem ============================================================================

:handle_start
call :ensure_env
shift
set "AUTO_OPEN=false"
set "PASSTHROUGH_ARGS="

:start_parse_loop
if "%~1"=="" goto start_parse_done
if /i "%~1"=="--open" (
    set "AUTO_OPEN=true"
) else if /i "%~1"=="-o" (
    set "AUTO_OPEN=true"
) else (
    set "PASSTHROUGH_ARGS=!PASSTHROUGH_ARGS! %1"
)
shift
goto start_parse_loop

:start_parse_done
echo [INFO] Starting Job Tracker in production background mode...
docker compose up -d --build !PASSTHROUGH_ARGS!
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker command failed. Please ensure Docker Desktop is running.
    exit /b %ERRORLEVEL%
)

echo.
echo ================================================================================
echo  Job Tracker is running permanently in the background!
echo --------------------------------------------------------------------------------
echo  Web Application:   http://localhost:4173
echo  API Documentation: http://localhost:8008/docs
echo.
echo  Quick Commands:
echo    jt status        Check container status
echo    jt logs          View live container logs
echo    jt stop          Stop all containers
echo    jt open          Open web app in browser
echo ================================================================================

if /i "!AUTO_OPEN!"=="true" (
    timeout /t 2 >nul
    start http://localhost:4173
)
exit /b 0

:handle_dev
call :ensure_env
shift
echo [INFO] Starting Job Tracker in LIVE DEVELOPMENT mode (Hot Reloading)...
echo  - Frontend (Vite HMR):  http://localhost:5173
echo  - Backend API (Proxy): http://localhost:5173/api
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %ERRORLEVEL%

:handle_stop
shift
echo [INFO] Stopping Job Tracker production containers...
docker compose down %1 %2 %3 %4 %5 %6 %7 %8 %9
echo [OK] Containers stopped.
exit /b 0

:handle_status
shift
echo [INFO] Job Tracker Container Status:
docker compose ps %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b 0

:handle_logs
shift
echo [INFO] Streaming Job Tracker container logs (Ctrl+C to exit)...
docker compose logs -f %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b 0

:handle_open
echo [INFO] Opening Job Tracker in default browser...
start http://localhost:4173
exit /b 0

:handle_update
call :ensure_env
shift
echo [INFO] Updating Job Tracker...
echo 1. Pulling latest base images...
docker compose pull
echo 2. Rebuilding and starting containers...
docker compose up -d --build %1 %2 %3 %4 %5 %6 %7 %8 %9
echo 3. Applying database migrations (Alembic)...
docker compose exec -T backend python -m alembic upgrade head 2>nul || docker compose exec -T backend uv run alembic upgrade head 2>nul || echo [WARN] Migration step finished.
echo.
echo ================================================================================
echo  Job Tracker successfully updated and database migrations applied!
echo --------------------------------------------------------------------------------
echo  Web Application:   http://localhost:4173
echo  API Documentation: http://localhost:8008/docs
echo ================================================================================
exit /b 0

:handle_reset
shift
set "FORCE=false"
if /i "%~1"=="--yes" set "FORCE=true"
if /i "%~1"=="-y" set "FORCE=true"
if /i "%~1"=="--force" set "FORCE=true"
if /i "%~1"=="-f" set "FORCE=true"

if /i "!FORCE!"=="false" (
    echo [WARN] This will permanently wipe all Job Tracker PostgreSQL database data,
    echo        vector embeddings, and saved dossiers.
    set "CONFIRM="
    set /p CONFIRM="Are you sure you want to proceed? [y/N]: "
    if /i not "!CONFIRM!"=="y" if /i not "!CONFIRM!"=="yes" (
        echo [INFO] Operation cancelled.
        exit /b 0
    )
)

echo [INFO] Stopping containers and wiping database volumes...
docker compose down -v --remove-orphans
docker volume rm -f job_tracker_postgres_data 2>nul
echo [OK] Database volume wiped clean. Fresh database will be created on next start.
exit /b 0

:handle_seed
shift
echo [INFO] Synthesizing mock technical job leads using Local LLM...
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m app.services.mock_generator --seed-db 2>nul || docker compose exec backend python -m app.services.mock_generator --seed-db
exit /b 0

:handle_help
:handle_unknown
if not "%COMMAND%"=="help" if not "%COMMAND%"=="-h" if not "%COMMAND%"=="--help" if not "%COMMAND%"=="/?" if not "%COMMAND%"=="-?" (
    echo [ERROR] Unknown command: '%COMMAND%'
    echo.
)
echo Job Tracker (jt.cmd) - Windows Command Reference
echo.
echo Usage:
echo   jt [command] [options]
echo.
echo Commands:
echo   start, up      Start Job Tracker in production background mode (default if no args)
echo                  Use 'jt start --open' or 'jt start -o' to auto-launch browser
echo   dev            Start Job Tracker in live development mode (Hot Reloading)
echo   stop, down     Stop all Job Tracker containers
echo   status, ps     Show status and health of Job Tracker containers
echo   logs           Follow live container logs (Ctrl+C to exit)
echo   open           Open http://localhost:4173 in default browser
echo   update         Rebuild containers and apply database migrations (Alembic)
echo   reset          Wipe database and application data after confirmation
echo   seed           Run dynamic local LLM mock data generator
echo   help, -h, /?   Display this command reference
echo.
echo Examples:
echo   jt                     Start production mode in background
echo   jt start --open        Start production and open browser
echo   jt dev                 Start development environment
echo   jt logs -f backend     Stream backend service logs
echo   jt status              Check status of all containers
echo   jt update              Update images, rebuild, and apply migrations
echo   jt stop                Stop background containers
echo.
exit /b 0
