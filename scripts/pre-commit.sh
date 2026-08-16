#!/usr/bin/env bash
set -e

# Repository Root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
echo ">> 3. Backend: Running pytest suite..."
(cd "$REPO_ROOT/backend" && uv run pytest)

echo ""
echo ">> 4. Frontend: Building and validating TypeScript..."
(cd "$REPO_ROOT/frontend" && npm run build)

echo ""
echo "==========================================="
echo "  All Pre-Commit Checks Passed! 🎉"
echo "==========================================="
