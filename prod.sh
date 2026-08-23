#!/usr/bin/env bash
# ==============================================================================
# Job Tracker - Production Environment Launcher
# ==============================================================================
set -e

RESET_DB=false
RESET_ONLY=false
STOP_ONLY=false
STATUS_ONLY=false
LOGS_ONLY=false
USE_EXTERNAL=false
DOCKER_ARGS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --external)
      USE_EXTERNAL=true
      shift
      ;;
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
    --status|-s)
      STATUS_ONLY=true
      shift
      ;;
    --logs|-l)
      LOGS_ONLY=true
      shift
      ;;
    --help|-h)
      echo "Job Tracker - Production Launcher"
      echo ""
      echo "Usage: ./prod.sh [OPTIONS] [DOCKER_COMPOSE_ARGS...]"
      echo ""
      echo "Options:"
      echo "  --external                         Use external PostgreSQL/Camofox (via docker-compose.external.yml)"
      echo "  --reset, --clean, -r, --reset-db   Wipe PostgreSQL database & application data, then start fresh"
      echo "  --reset-only                       Wipe database & data volumes without restarting containers"
      echo "  --down, --stop                     Stop running production containers"
      echo "  --status, -s                       Show status of production containers"
      echo "  --logs, -l                         View / follow production logs"
      echo "  --help, -h                         Show this help message"
      echo ""
      echo "Persistence & Boot Behavior:"
      echo "  Containers run permanently with 'restart: unless-stopped'."
      echo "  They will automatically start on PC/system boot whenever the Docker service runs."
      echo "  Containers will only stop when you explicitly run './prod.sh --down'."
      echo ""
      echo "Examples:"
      echo "  ./prod.sh                          # Normal permanent start in background (preserves DB data)"
      echo "  ./prod.sh --status                 # Check container status"
      echo "  ./prod.sh --logs                   # Tail logs from all containers"
      echo "  ./prod.sh --down                   # Stop production containers"
      echo "  ./prod.sh --reset                  # Reset DB data and start fresh"
      exit 0
      ;;
    *)
      DOCKER_ARGS+=("$1")
      shift
      ;;
  esac
done

if [ "$STATUS_ONLY" = true ]; then
  echo "📊 Production Container Status:"
  docker compose ps
  exit 0
fi

if [ "$LOGS_ONLY" = true ]; then
  echo "📋 Streaming Production Container Logs (Ctrl+C to exit)..."
  docker compose logs -f "${DOCKER_ARGS[@]}"
  exit 0
fi

if [ "$STOP_ONLY" = true ]; then
  echo "🛑 Stopping Job Tracker production containers..."
  docker compose down
  echo "✅ Containers stopped. (Will NOT restart on PC boot until started again)"
  exit 0
fi

if [ "$RESET_DB" = true ]; then
  echo "⚠️  RESETTING DATABASE & APPLICATION DATA..."
  echo "   Stopping containers and wiping volume: job_tracker_postgres_data..."
  docker compose down -v --remove-orphans
  docker volume rm -f job_tracker_postgres_data 2>/dev/null || true
  echo "🧹 Database volume wiped clean."
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

echo "🚀 Starting Job Tracker in PERMANENT PRODUCTION mode..."
echo " - Web Application & Ingress: http://localhost:4173"
echo " - API Docs (Swagger UI):     http://localhost:4173/api/docs"
echo " - Internal Services:         Backend, Database & Scraper (Isolated in Docker Network)"
COMPOSE_FILES=(-f docker-compose.yml)
if [ "$USE_EXTERNAL" = true ]; then
  COMPOSE_FILES+=(-f docker-compose.external.yml)
fi

docker compose "${COMPOSE_FILES[@]}" up -d --build "${DOCKER_ARGS[@]}"

CLI_CMD="${CLI_CMD:-jt}"

echo ""
echo "================================================================================"
echo " ✅ Job Tracker is running permanently in the background!"
echo "--------------------------------------------------------------------------------"
echo " 🔄 Auto-Start Policy: restart: unless-stopped"
echo "    - Containers will automatically start on PC boot whenever Docker is active."
echo "    - Containers will only stop if you explicitly run '${CLI_CMD} stop'."
echo ""
echo " 🌐 Web Application: http://localhost:4173"
echo " 📚 API Docs:        http://localhost:4173/api/docs"
echo ""
echo " 💡 Quick Management Commands:"
echo "    ${CLI_CMD} status    # Check running services"
echo "    ${CLI_CMD} logs      # View live logs"
echo "    ${CLI_CMD} stop      # Stop containers"
echo "================================================================================"
