#!/usr/bin/env bash
# ==============================================================================
# Job Tracker - Development Environment Manager
# Supports Live Hot-Reloading and Full Database / Application Reset
# ==============================================================================
set -e

RESET_DB=false
RESET_ONLY=false
STOP_ONLY=false
REFRESH_MOCKS=false
DOCKER_ARGS=()
COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.dev.yml)

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --reset|--clean|-r|--reset-db)
      RESET_DB=true
      shift
      ;;
    --reset-only)
      RESET_DB=true
      RESET_ONLY=true
      shift
      ;;
    --refresh-mocks|--refresh-seed)
      REFRESH_MOCKS=true
      shift
      ;;
    --down|--stop)
      STOP_ONLY=true
      shift
      ;;
    --seed-db|--seed)
      echo "🌱 Seeding mock development dataset..."
      if [ -x "$(command -v uv)" ]; then
        (cd backend && uv run python -m app.services.seed_data --force)
      else
        docker compose "${COMPOSE_FILES[@]}" exec backend python -m app.services.seed_data --force
      fi
      exit 0
      ;;
    --generate-mocks|--gen-mocks)
      echo "🤖 Running Dynamic Local LLM Mock Generator..."
      if [ -x "$(command -v uv)" ]; then
        (cd backend && uv run python -m app.services.mock_generator --seed-db)
      else
        docker compose "${COMPOSE_FILES[@]}" exec backend python -m app.services.mock_generator --seed-db
      fi
      exit 0
      ;;
    --help|-h)
      echo "Job Tracker - Development Launcher"
      echo ""
      echo "Usage: ./dev.sh [OPTIONS] [DOCKER_COMPOSE_ARGS...]"
      echo ""
      echo "Options:"
      echo "  --reset, --clean, -r, --reset-db   Wipe PostgreSQL database & application data, then start fresh"
      echo "  --reset-only                       Wipe database & data volumes without restarting containers"
      echo "  --refresh-mocks, --refresh-seed    Reset and reseed mock data in running containers"
      echo "  --seed-db, --seed                  Seed mock development dataset into backend database"
      echo "  --generate-mocks, --gen-mocks      Synthesize fresh mock domain data using Local LM Studio"
      echo "  --down, --stop                     Stop running development containers"
      echo "  --help, -h                         Show this help message"
      echo ""
      echo "Examples:"
      echo "  ./dev.sh                           # Normal start (preserves DB data)"
      echo "  ./dev.sh --reset                   # Reset all DB & app data and start fresh"
      echo "  ./dev.sh --generate-mocks          # Generate synthetic mock leads from local LLM"
      echo "  ./dev.sh --reset-only              # Wipe volumes and exit"
      echo "  ./dev.sh --refresh-mocks           # Refresh mock data without restarting containers"
      echo "  ./dev.sh --down                    # Stop containers"
      exit 0
      ;;
    *)
      DOCKER_ARGS+=("$1")
      shift
      ;;
  esac
done

COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.dev.yml)

if [ "$STOP_ONLY" = true ]; then
  echo "🛑 Stopping Job Tracker development containers..."
  docker compose "${COMPOSE_FILES[@]}" down
  echo "✅ Containers stopped."
  exit 0
fi

if [ "$RESET_DB" = true ]; then
  echo "⚠️  RESETTING DATABASE & APPLICATION DATA..."
  echo "   Stopping containers and wiping volumes: job_tracker_postgres_data, job_tracker_app_data..."
  docker compose "${COMPOSE_FILES[@]}" down -v --remove-orphans
  
  # Ensure named volumes are explicitly removed if detached
  docker volume rm -f job_tracker_postgres_data job_tracker_app_data 2>/dev/null || true
  
  echo "🧹 Database and application volumes wiped clean."
  echo ""

  if [ "$RESET_ONLY" = true ]; then
    echo "✅ Reset complete. Exiting without starting containers."
    exit 0
  fi
fi

# Ensure .env exists with sensible defaults
if [ ! -f .env ] && [ -f .env.example ]; then
  echo "📝 Creating initial .env from .env.example..."
  cp .env.example .env
fi

echo "🚀 Starting Job Tracker in LIVE DEVELOPMENT mode..."
echo " - Frontend (Vite HMR):   http://localhost:5173"
echo " - Backend API (Proxied):  http://localhost:5173/api"
echo " - Database & Scraper:    Internal Docker Network"
if [ "$RESET_DB" = true ]; then
  echo " - Database Status:       FRESH / INITIALIZED"
else
  echo " - Database Status:       Data Persisted (use './dev.sh --reset' to wipe)"
fi
echo ""

if [ "$REFRESH_MOCKS" = true ]; then
  echo "🔄 Resetting and reseeding mock development data..."
  docker compose "${COMPOSE_FILES[@]}" exec -T backend \
    python -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://localhost:8000/api/v1/admin/reset-database?confirm=true', method='DELETE', headers={'X-Confirm-Reset': 'true'}), timeout=30).read()"
  docker compose "${COMPOSE_FILES[@]}" exec -T backend \
    python -m app.services.seed_data --force
  echo "✅ Mock development data refreshed."
  exit 0
fi

docker compose "${COMPOSE_FILES[@]}" up --build -d "${DOCKER_ARGS[@]}"
