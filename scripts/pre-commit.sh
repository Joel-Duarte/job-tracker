#!/usr/bin/env bash
set -e

# Repository Root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RUN_ALL_DOCKER=false
if [[ "$1" == "--docker" || "$1" == "--all" ]]; then
  RUN_ALL_DOCKER=true
fi

echo "==========================================="
echo "  Running Pre-Commit Verification Pipeline"
echo "==========================================="

echo ""
echo ">> 1. Backend: Checking formatting with Ruff..."
(cd "$REPO_ROOT/backend" && uv run ruff format --check .)

echo ""
echo ">> 2. Backend: Linting with Ruff..."
(cd "$REPO_ROOT/backend" && uv run ruff check .)

echo ""
if [ "$RUN_ALL_DOCKER" = true ]; then
  echo ">> 3. Backend: Running full pytest suite (including Docker / Testcontainers)..."
  (cd "$REPO_ROOT/backend" && uv run pytest)
else
  echo ">> 3. Backend: Running fast pytest suite (excluding Docker)..."
  echo "   (Tip: Pass './scripts/pre-commit.sh --docker' to run full containerized tests)"
  (cd "$REPO_ROOT/backend" && uv run pytest -m "not docker")
fi

echo ""
echo ">> 4. Frontend: Building and validating TypeScript..."
(cd "$REPO_ROOT/frontend" && npm run build)

echo ""
echo "==========================================="
echo "  All Pre-Commit Checks Passed! 🎉"
echo "==========================================="
