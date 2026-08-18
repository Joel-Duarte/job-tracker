docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db
cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 &
cd frontend && npm run dev &
