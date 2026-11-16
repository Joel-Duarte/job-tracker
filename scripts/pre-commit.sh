#!/usr/bin/env bash
set -e

# Repository Root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAST_MODE=false
WITH_LLM_EVAL=false
for arg in "$@"; do
  case "$arg" in
    --fast|--no-docker|--skip-docker) FAST_MODE=true ;;
    --with-llm-eval) WITH_LLM_EVAL=true ;;
  esac
done

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

if [ "$WITH_LLM_EVAL" = true ] || [ "${RUN_LLM_EVAL:-0}" = "1" ]; then
  echo ""
  echo ">> 5. Local LLM Golden Eval Gate (concurrency-aware, prompt changes only)..."
  (cd "$REPO_ROOT/backend" && PYTHONPATH=. uv run python scripts/run_local_llm_gate.py --base origin/master --allow-offline)
fi

echo ""
echo "==========================================="
echo "  All Pre-Commit Checks Passed! 🎉"
echo "==========================================="
