"""Tests for maintainer-started Jules UI QA reviews."""

import unittest
from unittest.mock import Mock, patch

import jules_ui_qa
from jules_issues import ApiError

SOURCE = {"name": "sources/github-owner-repo"}


class UITaskTests(unittest.TestCase):
    @patch.object(jules_ui_qa, "source_for_repo", return_value=SOURCE)
    def test_same_repo_ui_pr_starts_review_without_auto_pr(self, _source):
        client = Mock(repo="owner/repo")
        client.gh.return_value = {
            "state": "open",
            "html_url": "https://github.test/owner/repo/pull/12",
            "base": {"ref": "master"},
            "head": {"ref": "feature/ui", "repo": {"full_name": "owner/repo"}},
        }
        client.pages.return_value = [
            {"filename": "frontend/src/views/CompaniesView.vue"},
            {"filename": "backend/app/main.py"},
        ]
        jules_ui_qa.start_ui_qa_task(client, 12)
        payload = client.jules.call_args.args[2]
        self.assertNotIn("automationMode", payload)
        self.assertEqual(
            payload["sourceContext"]["githubRepoContext"]["startingBranch"],
            "feature/ui",
        )
        self.assertIn("CompaniesView.vue", payload["prompt"])
        self.assertNotIn("backend/app/main.py", payload["prompt"])

    def test_rejects_fork_or_non_ui_pr(self):
        client = Mock(repo="owner/repo")
        client.gh.return_value = {
            "state": "open",
            "base": {"ref": "master"},
            "head": {"ref": "fix", "repo": {"full_name": "someone/repo"}},
        }
        with self.assertRaisesRegex(ApiError, "branches in this repository"):
            jules_ui_qa.start_ui_qa_task(client, 12)
        client.gh.return_value["head"]["repo"]["full_name"] = "owner/repo"
        client.pages.return_value = [{"filename": "backend/app/main.py"}]
        with self.assertRaisesRegex(ApiError, "no frontend changes"):
            jules_ui_qa.start_ui_qa_task(client, 12)
        client.jules.assert_not_called()

    def test_rejects_invalid_number(self):
        client = Mock()
        for value in (0, "abc", None):
            with self.assertRaisesRegex(ApiError, "positive integer"):
                jules_ui_qa.start_ui_qa_task(client, value)
        client.gh.assert_not_called()


if __name__ == "__main__":
    unittest.main()
