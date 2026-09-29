"""Require Playwright test changes alongside frontend source changes in a PR."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_paths(paths):
    ui_sources = [
        path
        for path in paths
        if path.startswith("frontend/src/")
        and path.endswith((".vue", ".js", ".jsx", ".ts", ".tsx", ".css", ".scss"))
    ]
    qa_changes = [path for path in paths if path.startswith("frontend/tests/e2e/")]
    return ui_sources, qa_changes


def main(base, head):
    result = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only", base, head],
        check=True,
        capture_output=True,
        text=True,
    )
    ui_sources, qa_changes = check_paths(result.stdout.splitlines())
    if ui_sources and not qa_changes:
        print("Frontend source changed without a Playwright QA test update:")
        print("\n".join(ui_sources))
        print("Add or update a test under frontend/tests/e2e/ for the user behavior.")
        return 1
    print("UI QA coverage policy passed.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: check_ui_test_coverage.py BASE_SHA HEAD_SHA")
    sys.exit(main(sys.argv[1], sys.argv[2]))
