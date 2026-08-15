#!/usr/bin/env bash
# ==============================================================================
# Job Tracker - Start Development Environment with Hot-Reloading
# ==============================================================================
set -e

echo "🚀 Starting Job Tracker in LIVE DEVELOPMENT mode..."
echo " - Backend: Live reload on Python file edits (http://localhost:8008)"
echo " - Frontend: Vite HMR on Vue/CSS edits (http://localhost:5173)"
echo " - Database: PostgreSQL + pgvector (localhost:54320, data persisted)"
echo " - Scraper:  Camofox Automation (http://localhost:9355)"
echo ""

docker compose -f docker-compose.yml -f docker-compose.dev.yml up "$@"
