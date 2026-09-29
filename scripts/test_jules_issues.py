"""Focused tests for Jules issue event filtering and session handoff."""

import unittest
from unittest.mock import Mock, patch

import jules_issues as automation


def issue(labels=None):
    return {
        "number": 42,
        "title": "Broken board",
        "body": "Drag a card and observe the error",
        "state": "open",
        "labels": [{"name": name} for name in (labels or [])],
    }


class EventTests(unittest.TestCase):
    @patch.object(automation, "begin")
    def test_bug_open_starts_validation_only(self, begin):
        client = Mock()
        automation.handle_event(
            client, "issues", {"action": "opened", "issue": issue(["bug"])}
        )
        begin.assert_called_once_with(client, issue(["bug"]), "validate")
        begin.reset_mock()
        automation.handle_event(
            client, "issues", {"action": "opened", "issue": issue()}
        )
        begin.assert_not_called()

    @patch.object(automation, "begin")
    def test_maintainer_command_and_pr_filter(self, begin):
        client = Mock()
        client.repo = "owner/repo"
        client.request.return_value = {"permission": "write"}
        event = {
            "action": "created",
            "issue": issue(),
            "comment": {"body": "/jules fix", "user": {"login": "maintainer"}},
        }
        automation.handle_event(client, "issue_comment", event)
        begin.assert_called_once_with(client, issue(), "fix", force=True)
        begin.reset_mock()
        event["issue"]["pull_request"] = {"url": "https://example.test/pr"}
        automation.handle_event(client, "issue_comment", event)
        begin.assert_not_called()

    @patch.object(automation, "begin")
    def test_read_only_user_cannot_command_fix(self, begin):
        client = Mock()
        client.repo = "owner/repo"
        client.request.return_value = {"permission": "read"}
        automation.handle_event(
            client,
            "issue_comment",
            {
                "action": "created",
                "issue": issue(),
                "comment": {"body": "/jules fix", "user": {"login": "reader"}},
            },
        )
        begin.assert_not_called()


class ResultTests(unittest.TestCase):
    @patch.object(automation, "finish_validation")
    @patch.object(automation, "final_message", return_value="Result")
    @patch.object(
        automation,
        "state_comment",
        return_value=(7, {"kind": "validate", "session": "sessions/123"}),
    )
    def test_poller_hands_completed_validation_to_result_handler(
        self, state_comment, final_message, finish_validation
    ):
        client = Mock()
        pending_issue = issue(["jules:validating"])
        client.pages.side_effect = [iter([]), iter([pending_issue])]
        client.jules.return_value = {"state": "COMPLETED"}
        automation.poll(client)
        finish_validation.assert_called_once_with(
            client, pending_issue, {"state": "COMPLETED"}, "Result"
        )
        final_message.assert_called_once_with(client, "sessions/123")
        state_comment.assert_called_once_with(client, 42)

    def test_missing_state_label_is_created(self):
        client = Mock()
        client.gh.side_effect = [automation.ApiError("HTTP 404"), {}, {}]
        automation.add_label(client, 42, "jules:validating")
        self.assertEqual(client.gh.call_args_list[1].args[:2], ("POST", "/labels"))
        self.assertEqual(
            client.gh.call_args_list[2].args[:2], ("POST", "/issues/42/labels")
        )

    def test_validation_requires_explicit_evidence(self):
        self.assertIsNone(automation.validation_result("Looks broken."))
        self.assertIsNone(
            automation.validation_result(
                'JULES_VALIDATION_RESULT {"verdict":"REPRODUCED","evidence":"","next_steps":""}'
            )
        )
        result = automation.validation_result(
            'JULES_VALIDATION_RESULT {"verdict":"REPRODUCED",'
            '"evidence":"pytest test_board.py fails","next_steps":"fix handler"}'
        )
        self.assertEqual(result["verdict"], "REPRODUCED")

    @patch.object(automation, "remove_label")
    @patch.object(automation, "add_label")
    @patch.object(automation, "comment")
    @patch.object(automation, "write_state")
    @patch.object(automation, "new_session")
    def test_reproduced_bug_starts_fix(
        self, new_session, write_state, comment, add_label, remove_label
    ):
        client = Mock()
        new_session.return_value = {
            "name": "sessions/fix",
            "url": "https://jules.test/fix",
        }
        message = (
            'JULES_VALIDATION_RESULT {"verdict":"REPRODUCED",'
            '"evidence":"failing test_board.py","next_steps":""}'
        )
        automation.finish_validation(
            client, issue(["jules:validating"]), {"state": "COMPLETED"}, message
        )
        new_session.assert_called_once_with(
            client, issue(["jules:validating"]), "fix", "failing test_board.py"
        )
        write_state.assert_called_once()
        add_label.assert_called_once_with(client, 42, "jules:fixing")
        remove_label.assert_called_once_with(client, 42, "jules:validating")
        self.assertIn("failing test_board.py", comment.call_args.args[2])

    @patch.object(automation, "remove_label")
    @patch.object(automation, "add_label")
    @patch.object(automation, "comment")
    @patch.object(automation, "new_session")
    def test_inconclusive_bug_stays_on_issue(
        self, new_session, comment, add_label, remove_label
    ):
        automation.finish_validation(
            Mock(),
            issue(),
            {"state": "COMPLETED", "url": "https://jules.test/check"},
            "Cannot reproduce.",
        )
        new_session.assert_not_called()
        add_label.assert_called_once()
        self.assertEqual(add_label.call_args.args[2], "jules:needs-info")
        self.assertIn("Cannot reproduce", comment.call_args.args[2])
        remove_label.assert_called_once()

    @patch.object(automation, "remove_label")
    @patch.object(automation, "add_label")
    @patch.object(automation, "comment")
    def test_failed_fix_reports_without_pr(self, comment, add_label, remove_label):
        automation.finish_fix(
            Mock(),
            issue(),
            {"outputs": [], "url": "https://jules.test/fix"},
            "Use a stable card id.",
        )
        self.assertIn("Use a stable card id", comment.call_args.args[2])
        self.assertEqual(add_label.call_args.args[2], "jules:needs-info")
        remove_label.assert_called_once()


if __name__ == "__main__":
    unittest.main()
