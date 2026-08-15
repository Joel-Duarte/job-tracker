#!/usr/bin/env bash
# ==============================================================================
# Job Tracker - Start Production Environment
# ==============================================================================
set -e

echo "🚀 Starting Job Tracker in PRODUCTION mode..."
echo " - Frontend: Production Nginx SPA & Reverse Proxy (http://localhost:4173)"
echo " - Backend:  FastAPI Production Workers (http://localhost:8008)"
echo " - Database: PostgreSQL + pgvector (localhost:54320, data persisted)"
echo " - Scraper:  Camofox Automation (http://localhost:9355)"
echo ""

docker compose up -d "$@"
