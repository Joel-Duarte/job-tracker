"""Tests for the manual security-alert handoff to Jules."""

import unittest
from unittest.mock import Mock, patch

import jules_security as security
from jules_issues import ApiError

SOURCE = {
    "name": "sources/github-owner-repo",
    "githubRepo": {"defaultBranch": {"displayName": "master"}},
}


class SecurityTaskTests(unittest.TestCase):
    @patch.object(security, "source_for_repo", return_value=SOURCE)
    def test_codeql_alert_starts_reviewable_session_without_pr(self, source_for_repo):
        client = Mock()
        client.gh.return_value = {
            "state": "open",
            "html_url": "https://github.test/code-scanning/42",
            "rule": {
                "id": "py/path-injection",
                "description": "Path injection",
                "security_severity_level": "high",
            },
            "most_recent_instance": {
                "ref": "refs/heads/master",
                "state": "open",
                "location": {"path": "backend/app/file.py", "start_line": 12},
                "message": {"text": "User input reaches a file path"},
            },
        }
        client.jules.return_value = {
            "name": "sessions/123",
            "url": "https://jules.test/123",
        }
        security.start_security_task(client, "codeql", 42)
        client.gh.assert_called_once_with("GET", "/code-scanning/alerts/42")
        payload = client.jules.call_args.args[2]
        self.assertNotIn("automationMode", payload)
        self.assertEqual(
            payload["sourceContext"]["githubRepoContext"]["startingBranch"], "master"
        )
        self.assertIn("backend/app/file.py:12", payload["prompt"])
        source_for_repo.assert_called_once_with(client)

    @patch.object(security, "source_for_repo", return_value=SOURCE)
    def test_dependabot_alert_includes_patch_version(self, _source_for_repo):
        client = Mock()
        client.gh.return_value = {
            "state": "open",
            "html_url": "https://github.test/dependabot/8",
            "dependency": {
                "manifest_path": "frontend/package-lock.json",
                "package": {"ecosystem": "npm", "name": "example"},
            },
            "security_advisory": {
                "ghsa_id": "GHSA-0000",
                "summary": "Example flaw",
                "severity": "high",
            },
            "security_vulnerability": {
                "vulnerable_version_range": "<2.0.0",
                "first_patched_version": {"identifier": "2.0.0"},
            },
        }
        security.start_security_task(client, "dependabot", "8")
        payload = client.jules.call_args.args[2]
        self.assertIn("GHSA-0000", payload["prompt"])
        self.assertIn("2.0.0", payload["prompt"])
        self.assertNotIn("automationMode", payload)

    @patch.object(security, "source_for_repo", return_value=SOURCE)
    def test_rejects_closed_or_pr_only_codeql_alert(self, _source_for_repo):
        client = Mock()
        client.gh.return_value = {"state": "dismissed"}
        with self.assertRaisesRegex(ApiError, "not open"):
            security.start_security_task(client, "codeql", 42)
        client.gh.return_value = {
            "state": "open",
            "html_url": "https://github.test/code-scanning/42",
            "rule": {"security_severity_level": "high"},
            "most_recent_instance": {"ref": "refs/pull/10/merge", "state": "open"},
        }
        with self.assertRaisesRegex(ApiError, "default branch"):
            security.start_security_task(client, "codeql", 42)
        client.jules.assert_not_called()

    def test_rejects_invalid_inputs_before_any_api_call(self):
        client = Mock()
        for kind, number in (("secret", "1"), ("codeql", "0"), ("codeql", "bad")):
            with self.assertRaises(ApiError):
                security.start_security_task(client, kind, number)
        client.gh.assert_not_called()
        client.jules.assert_not_called()


if __name__ == "__main__":
    unittest.main()
