#!/usr/bin/env bash
# ==============================================================================
# Job Tracker - Development Environment Manager
# Supports Live Hot-Reloading and Full Database / Application Reset
# ==============================================================================
set -e

RESET_DB=false
RESET_ONLY=false
STOP_ONLY=false
DOCKER_ARGS=()

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
    --down|--stop)
      STOP_ONLY=true
      shift
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
      echo "  --generate-mocks, --gen-mocks      Synthesize fresh mock domain data using Local LM Studio"
      echo "  --down, --stop                     Stop running development containers"
      echo "  --help, -h                         Show this help message"
      echo ""
      echo "Examples:"
      echo "  ./dev.sh                           # Normal start (preserves DB data)"
      echo "  ./dev.sh --reset                   # Reset all DB & app data and start fresh"
      echo "  ./dev.sh --generate-mocks          # Generate synthetic mock leads from local LLM"
      echo "  ./dev.sh --reset-only              # Wipe volumes and exit"
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
  echo "   Stopping containers and wiping database volumes..."
  docker compose "${COMPOSE_FILES[@]}" down -v --remove-orphans --timeout 2 2>/dev/null || true
  
  # Ensure all related containers and volumes are forcefully removed
  docker rm -f job-tracker-postgresdb job-tracker-backend job-tracker-frontend-dev job-tracker-scraper 2>/dev/null || true
  docker volume rm -f job_tracker_postgres_data job-tracker_postgres_data 2>/dev/null || true
  docker volume prune -f --filter "label=com.docker.compose.project=job-tracker" 2>/dev/null || true
  
  echo "🧹 Database volume wiped clean. A fresh database will be initialized on boot."
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
echo " - Frontend (Vite HMR):       http://localhost:5173"
echo " - Backend API (Proxied):      http://localhost:5173/api"
echo " - API Docs (Swagger UI):     http://localhost:5173/api/docs"
echo " - Database & Scraper:        Internal Docker Network"
if [ "$RESET_DB" = true ]; then
  echo " - Database Status:       FRESH / INITIALIZED"
else
  echo " - Database Status:       Data Persisted (use './dev.sh --reset' to wipe)"
fi
echo ""

docker compose "${COMPOSE_FILES[@]}" up --build "${DOCKER_ARGS[@]}"
