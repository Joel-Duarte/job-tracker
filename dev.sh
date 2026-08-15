#!/usr/bin/env bash
# ==============================================================================
# Job Tracker - Start Development Environment with Hot-Reloading
# ==============================================================================
set -e

echo "🚀 Starting Job Tracker in LIVE DEVELOPMENT mode..."
echo " - Frontend (Vite HMR):  http://localhost:5173"
echo " - Backend API (Proxied): http://localhost:5173/api"
echo " - Database & Scraper:   Internal Docker Network (data persisted)"
echo ""

docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build "$@"
