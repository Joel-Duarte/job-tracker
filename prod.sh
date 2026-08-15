#!/usr/bin/env bash
# ==============================================================================
# Job Tracker - Production Environment Launcher
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
    --help|-h)
      echo "Job Tracker - Production Launcher"
      echo ""
      echo "Usage: ./prod.sh [OPTIONS] [DOCKER_COMPOSE_ARGS...]"
      echo ""
      echo "Options:"
      echo "  --reset, --clean, -r, --reset-db   Wipe PostgreSQL database & application data, then start fresh"
      echo "  --reset-only                       Wipe database & data volumes without restarting containers"
      echo "  --down, --stop                     Stop running production containers"
      echo "  --help, -h                         Show this help message"
      echo ""
      echo "Examples:"
      echo "  ./prod.sh                          # Normal start in background (preserves DB data)"
      echo "  ./prod.sh --reset                  # Reset DB data and start fresh"
      echo "  ./prod.sh --down                   # Stop production containers"
      exit 0
      ;;
    *)
      DOCKER_ARGS+=("$1")
      shift
      ;;
  esac
done

if [ "$STOP_ONLY" = true ]; then
  echo "🛑 Stopping Job Tracker production containers..."
  docker compose down
  echo "✅ Containers stopped."
  exit 0
fi

if [ "$RESET_DB" = true ]; then
  echo "⚠️  RESETTING DATABASE & APPLICATION DATA..."
  echo "   Stopping containers and wiping volumes: job_tracker_postgres_data, job_tracker_app_data..."
  docker compose down -v --remove-orphans
  docker volume rm -f job_tracker_postgres_data job_tracker_app_data 2>/dev/null || true
  echo "🧹 Database and application volumes wiped clean."
  echo ""

  if [ "$RESET_ONLY" = true ]; then
    echo "✅ Reset complete. Exiting without starting containers."
    exit 0
  fi
fi

echo "🚀 Starting Job Tracker in PRODUCTION mode..."
echo " - Frontend: Production Nginx SPA & Reverse Proxy (http://localhost:4173)"
echo " - Backend:  FastAPI Production Workers (http://localhost:8008)"
echo " - Database: PostgreSQL + pgvector (localhost:54320, data persisted)"
echo " - Scraper:  Camofox Automation (http://localhost:9355)"
echo ""

docker compose up -d --build "${DOCKER_ARGS[@]}"
