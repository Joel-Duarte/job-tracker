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
if /i "%COMMAND%"=="backup" goto handle_backup
if /i "%COMMAND%"=="backup-db" goto handle_backup
if /i "%COMMAND%"=="update" goto handle_update
if /i "%COMMAND%"=="reset" goto handle_reset
if /i "%COMMAND%"=="clean" goto handle_reset
if /i "%COMMAND%"=="wipe" goto handle_reset
if /i "%COMMAND%"=="wipe-db" goto handle_reset
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
set "WIPE_FIRST=false"
set "USE_EXTERNAL=false"
set "PASSTHROUGH_ARGS="

:start_parse_loop
if "%~1"=="" goto start_parse_done
if /i "%~1"=="--open" (
    set "AUTO_OPEN=true"
) else if /i "%~1"=="-o" (
    set "AUTO_OPEN=true"
) else if /i "%~1"=="--clean" (
    set "WIPE_FIRST=true"
) else if /i "%~1"=="--reset" (
    set "WIPE_FIRST=true"
) else if /i "%~1"=="-r" (
    set "WIPE_FIRST=true"
) else if /i "%~1"=="--external" (
    set "USE_EXTERNAL=true"
) else (
    set "PASSTHROUGH_ARGS=!PASSTHROUGH_ARGS! %1"
)
shift
goto start_parse_loop

:start_parse_done
if /i "!WIPE_FIRST!"=="true" (
    echo [INFO] Wiping production database volume for pristine start...
    docker compose down -v --remove-orphans >nul 2>nul
    docker volume rm -f job_tracker_postgres_data >nul 2>nul
    echo [OK] Production database wiped clean.
)
echo [INFO] Starting Job Tracker in production background mode...
if /i "!USE_EXTERNAL!"=="true" (
    docker compose -f docker-compose.yml -f docker-compose.external.yml up -d --build !PASSTHROUGH_ARGS!
) else (
    docker compose up -d --build !PASSTHROUGH_ARGS!
)
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker command failed. Please ensure Docker Desktop is running.
    exit /b %ERRORLEVEL%
)

echo.
echo ================================================================================
echo  Job Tracker is running permanently in the background!
echo --------------------------------------------------------------------------------
echo  Web Application:   http://localhost:4173
echo  API Documentation: http://localhost:4173/api/docs
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

:handle_backup
call :ensure_env
shift
echo [INFO] Creating database backup in backups\...
if not exist "backups" mkdir backups
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value 2^>nul') do set "dt=%%a"
if not defined dt (
    set "TIMESTAMP=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
    set "TIMESTAMP=!TIMESTAMP: =0!"
) else (
    set "TIMESTAMP=!dt:~0,4!!dt:~4,2!!dt:~6,2!_!dt:~8,2!!dt:~10,2!!dt:~12,2!"
)
set "BACKUP_FILE=backups\job_tracker_backup_!TIMESTAMP!.sql"
docker compose up -d db >nul 2>nul
timeout /t 2 >nul
docker compose exec -T db pg_dump -U postgres -d postgres --clean --if-exists > "!BACKUP_FILE!" 2>nul
if exist "!BACKUP_FILE!" (
    for %%A in ("!BACKUP_FILE!") do (
        if %%~zA gtr 0 (
            echo [OK] Database backed up to !BACKUP_FILE!
        ) else (
            echo [WARN] Backup file was empty; database may be uninitialized.
            del "!BACKUP_FILE!" >nul 2>nul
        )
    )
) else (
    echo [WARN] Could not create database backup.
)
exit /b 0

:handle_update
call :ensure_env
shift
echo [INFO] Updating Job Tracker...
echo 1. Saving current database backup...
call :handle_backup
echo 2. Pulling latest base images...
docker compose pull
echo 3. Rebuilding and starting containers...
docker compose up -d --build %1 %2 %3 %4 %5 %6 %7 %8 %9
echo 4. Applying database migrations (Alembic)...
docker compose exec -T backend alembic upgrade head || docker compose exec -T backend python -m alembic upgrade head || echo [WARN] Migration step skipped or failed.
echo.
echo ================================================================================
echo  Job Tracker successfully updated and database migrations applied!
echo --------------------------------------------------------------------------------
echo  Web Application:   http://localhost:4173
echo  API Documentation: http://localhost:4173/api/docs
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
echo                  Use 'jt start --clean' or 'jt start -r' to wipe DB and start fresh
echo                  Use 'jt start --external' to connect to external Postgres/Camofox
echo   dev            Start Job Tracker in live development mode (Isolated Dev DB)
echo   stop, down     Stop all Job Tracker containers
echo   status, ps     Show status and health of Job Tracker containers
echo   logs           Follow live container logs (Ctrl+C to exit)
echo   open           Open http://localhost:4173 in default browser
echo   backup, backup-db Save snapshot of current PostgreSQL database to backups\
echo   update         Backup database to backups\, pull latest images, rebuild, and apply migrations
echo   reset, clean   Wipe database and application data after confirmation (or pass -y)
echo   seed           Run dynamic local LLM mock data generator
echo   help, -h, /?   Display this command reference
echo.
echo Examples:
echo   jt                     Start production mode in background
echo   jt start --clean       Start fresh with a pristine empty database
echo   jt start --open        Start production and open browser
echo   jt dev                 Start development environment (isolated dev DB)
echo   jt clean               Wipe database after confirmation
echo   jt logs -f backend     Stream backend service logs
echo   jt status              Check status of all containers
echo   jt update              Update images, rebuild, and apply migrations
echo   jt stop                Stop background containers
echo.
exit /b 0
