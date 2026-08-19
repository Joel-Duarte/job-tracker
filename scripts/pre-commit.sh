#!/usr/bin/env bash
set -e

# Repository Root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAST_MODE=false
if [[ "$1" == "--fast" || "$1" == "--no-docker" || "$1" == "--skip-docker" ]]; then
  FAST_MODE=true
fi

echo "==========================================="
echo "  Running Pre-Commit Verification Pipeline"
echo "==========================================="

echo ""
echo ">> 1. Backend: Checking formatting with Ruff..."
(cd "$REPO_ROOT/backend" && uv run ruff format .)

echo ""
echo ">> 2. Backend: Linting with Ruff..."
(cd "$REPO_ROOT/backend" && uv run ruff check --fix .)

echo ""
if [ "$FAST_MODE" = true ]; then
  echo ">> 3. Backend: Running fast pytest suite (excluding Docker)..."
  (cd "$REPO_ROOT/backend" && uv run pytest -m "not docker")
else
  echo ">> 3. Backend: Running full pytest suite (including PostgreSQL / Testcontainers)..."
  echo "   (Tip: Pass './scripts/pre-commit.sh --fast' to skip container/db tests during quick local checks)"
  (cd "$REPO_ROOT/backend" && uv run pytest)
fi

echo ""
echo ">> 4. Frontend: Building and validating TypeScript..."
(cd "$REPO_ROOT/frontend" && npm run build)

echo ""
echo "==========================================="
echo "  All Pre-Commit Checks Passed! 🎉"
echo "==========================================="
