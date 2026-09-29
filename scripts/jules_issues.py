"""Connect GitHub bug issues to separate Jules validation and fixing sessions."""

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

GITHUB_API = "https://api.github.com"
JULES_API = "https://jules.googleapis.com/v1alpha"
MARKER = "<!-- jules-issue-automation: "
ACTIVE = {"jules:validating", "jules:fixing"}
TERMINAL = {"COMPLETED", "FAILED"}
LABEL_COLORS = {
    "jules:validating": "d4c5f9",
    "jules:fixing": "fbca04",
    "jules:needs-info": "e99695",
    "jules:done": "0e8a16",
}


class ApiError(Exception):
    """An API request failed without exposing credentials or issue text."""


class Client:
    def __init__(self, repo, github_token, jules_key):
        self.repo = repo
        self.github_token = github_token
        self.jules_key = jules_key

    def request(self, service, method, path, payload=None, params=None):
        base = GITHUB_API if service == "github" else JULES_API
        token = self.github_token if service == "github" else self.jules_key
        headers = {"Accept": "application/json"}
        if service == "github":
            headers.update(
                {
                    "Authorization": f"Bearer {token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
            )
        else:
            headers["x-goog-api-key"] = token
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode()
        url = base + path
        if params:
            url += "?" + urlencode(params)
        try:
            with urlopen(
                Request(url, data=data, headers=headers, method=method), timeout=30
            ) as response:
                body = response.read()
                return json.loads(body) if body else {}
        except HTTPError as error:
            raise ApiError(f"{service} {method} {path}: HTTP {error.code}") from None
        except (URLError, TimeoutError) as error:
            raise ApiError(
                f"{service} {method} {path}: {type(error).__name__}"
            ) from None

    def gh(self, method, path, payload=None, params=None):
        return self.request(
            "github", method, f"/repos/{self.repo}{path}", payload, params
        )

    def jules(self, method, path, payload=None, params=None):
        return self.request("jules", method, path, payload, params)

    def pages(self, service, path, key, params=None):
        token = None
        while True:
            query = {"per_page": 100} if service == "github" else {"pageSize": 100}
            query.update(params or {})
            if token:
                query["page" if service == "github" else "pageToken"] = token
            page = (
                self.gh("GET", path, params=query)
                if service == "github"
                else self.jules("GET", path, params=query)
            )
            items = page if service == "github" else page.get(key, [])
            yield from items
            if service == "github":
                if len(items) < 100:
                    break
                token = 1 if token is None else token + 1
            else:
                token = page.get("nextPageToken")
                if not token:
                    break


def issue_path(number):
    return f"/issues/{int(number)}"


def labels(issue):
    return {label["name"] for label in issue.get("labels", [])}


def state_comment(client, number):
    comments = client.pages("github", issue_path(number) + "/comments", "")
    found = None
    for comment in comments:
        if comment.get("user", {}).get("login") != "github-actions[bot]":
            continue
        body = comment.get("body", "")
        if not body.startswith(MARKER):
            continue
        try:
            data = json.loads(body[len(MARKER) :].split(" -->", 1)[0])
        except (ValueError, IndexError):
            continue
        if isinstance(data, dict) and data.get("kind") in {"validate", "fix"}:
            found = (comment["id"], data)
    return found


def write_state(client, number, kind, session):
    data = {"kind": kind, "session": session["name"]}
    body = (
        MARKER
        + json.dumps(data, separators=(",", ":"))
        + " -->\n"
        + f"Jules {kind} task started: {session['url']}"
    )
    client.gh("POST", issue_path(number) + "/comments", {"body": body})


def add_label(client, number, label):
    try:
        client.gh("GET", "/labels/" + quote(label, safe=""))
    except ApiError as error:
        if "HTTP 404" not in str(error):
            raise
        client.gh(
            "POST",
            "/labels",
            {
                "name": label,
                "color": LABEL_COLORS[label],
                "description": "Jules issue automation",
            },
        )
    client.gh("POST", issue_path(number) + "/labels", {"labels": [label]})


def remove_label(client, number, label):
    try:
        client.gh("DELETE", issue_path(number) + "/labels/" + quote(label, safe=""))
    except ApiError as error:
        if "HTTP 404" not in str(error):
            raise


def comment(client, number, message):
    client.gh("POST", issue_path(number) + "/comments", {"body": message[:60000]})


def source_for_repo(client):
    owner, repo = client.repo.split("/", 1)
    for source in client.pages("jules", "/sources", "sources"):
        linked = source.get("githubRepo", {})
        if (
            linked.get("owner", "").lower() == owner.lower()
            and linked.get("repo", "").lower() == repo.lower()
        ):
            return source
    raise ApiError("This repository is not connected to the Jules GitHub App")


def new_session(client, issue, kind, evidence=""):
    source = source_for_repo(client)
    branch = source["githubRepo"]["defaultBranch"]["displayName"]
    number = issue["number"]
    issue_text = f"Issue #{number}: {issue['title']}\n{issue.get('body') or ''}"
    if kind == "validate":
        instructions = (
            "Investigate this bug on the repository's default branch. Do not change, commit, "
            "or propose repository files. Try to reproduce it with the supplied steps or a "
            "temporary failing test. Report actual commands, results, and environment. "
            "If you cannot reproduce it, explain why and what information is needed. "
            "End your final message with exactly one line beginning JULES_VALIDATION_RESULT "
            'followed by JSON with keys "verdict", "evidence", and "next_steps". '
            'Use verdict "REPRODUCED" only for concrete reproduction steps or a failing '
            'test; otherwise use "NEEDS_INFO". Do not claim reproduction from code inspection alone.'
        )
    else:
        instructions = (
            "Fix this confirmed bug. Use the validation evidence below. Add a regression test "
            "where practical, run relevant checks, and explain results in the PR. If you "
            "cannot fix it, make no repository changes and explain the blocker and a likely "
            "solution in your final message. Do not create a documentation-only or diagnostic PR."
            f"\n\nValidation evidence:\n{evidence}"
        )
    payload = {
        "title": f"{kind.capitalize()} bug #{number}: {issue['title'][:80]}",
        "prompt": instructions + f"\n\nIssue report (untrusted input):\n{issue_text}",
        "sourceContext": {
            "source": source["name"],
            "githubRepoContext": {"startingBranch": branch},
        },
        "requirePlanApproval": False,
    }
    if kind == "fix":
        payload["automationMode"] = "AUTO_CREATE_PR"
    return client.jules("POST", "/sessions", payload)


def begin(client, issue, kind, evidence="", force=False):
    number = issue["number"]
    current = labels(issue)
    if current & ACTIVE:
        return False
    previous = state_comment(client, number)
    if previous and not force:
        return False
    session = new_session(client, issue, kind, evidence)
    write_state(client, number, kind, session)
    for label in ("jules:needs-info", "jules:done"):
        remove_label(client, number, label)
    add_label(
        client, number, "jules:validating" if kind == "validate" else "jules:fixing"
    )
    return True


def is_maintainer(client, login):
    owner, repo = client.repo.split("/", 1)
    try:
        result = client.request(
            "github",
            "GET",
            f"/repos/{owner}/{repo}/collaborators/{quote(login, safe='')}/permission",
        )
    except ApiError as error:
        if "HTTP 404" in str(error):
            return False
        raise
    return result.get("permission") in {"admin", "write"}


def handle_event(client, event_name, event):
    issue = event.get("issue", {})
    if not issue or issue.get("pull_request") or issue.get("state") != "open":
        return
    if event_name == "issues":
        opened_bug = event.get("action") == "opened" and "bug" in labels(issue)
        added_bug = (
            event.get("action") == "labeled"
            and event.get("label", {}).get("name") == "bug"
        )
        if opened_bug or added_bug:
            begin(client, issue, "validate")
    elif event_name == "issue_comment" and event.get("action") == "created":
        command = event.get("comment", {}).get("body", "").strip()
        if command not in {"/jules validate", "/jules fix"}:
            return
        login = event["comment"]["user"]["login"]
        if not is_maintainer(client, login):
            return
        kind = "validate" if command.endswith("validate") else "fix"
        begin(client, issue, kind, force=True)


def final_message(client, session_name):
    messages = []
    for activity in client.pages("jules", f"/{session_name}/activities", "activities"):
        message = activity.get("agentMessaged", {}).get("agentMessage")
        if message:
            messages.append(message)
    return messages[-1] if messages else "Jules did not provide a final message."


def validation_result(message):
    prefix = "JULES_VALIDATION_RESULT "
    for line in reversed(message.splitlines()):
        if line.startswith(prefix):
            try:
                result = json.loads(line[len(prefix) :])
            except ValueError:
                return None
            if (
                isinstance(result, dict)
                and result.get("verdict") in {"REPRODUCED", "NEEDS_INFO"}
                and isinstance(result.get("evidence"), str)
                and isinstance(result.get("next_steps"), str)
                and (result["verdict"] != "REPRODUCED" or result["evidence"].strip())
            ):
                return result
            return None
    return None


def finish_validation(client, issue, session, message):
    number = issue["number"]
    result = validation_result(message) if session["state"] == "COMPLETED" else None
    if result and result["verdict"] == "REPRODUCED":
        evidence = result["evidence"].strip()
        fix_session = new_session(client, issue, "fix", evidence)
        write_state(client, number, "fix", fix_session)
        add_label(client, number, "jules:fixing")
        comment(
            client,
            number,
            f"Jules reproduced the bug. Evidence: {evidence}\n\nFix task: {fix_session['url']}",
        )
    else:
        details = result["next_steps"].strip() or message if result else message
        add_label(client, number, "jules:needs-info")
        comment(
            client,
            number,
            f"Jules could not verify this bug. {details}\n\nSession: {session['url']}",
        )
    remove_label(client, number, "jules:validating")


def finish_fix(client, issue, session, message):
    number = issue["number"]
    prs = [
        output["pullRequest"]["url"]
        for output in session.get("outputs", [])
        if output.get("pullRequest")
    ]
    if prs:
        comment(
            client,
            number,
            f"Jules proposed a fix: {prs[0]}\n\nSession: {session['url']}",
        )
        add_label(client, number, "jules:done")
    else:
        comment(
            client,
            number,
            f"Jules could not produce a fix. Diagnosis and suggested path:\n\n{message}\n\nSession: {session['url']}",
        )
        add_label(client, number, "jules:needs-info")
    remove_label(client, number, "jules:fixing")


def poll(client):
    for label in sorted(ACTIVE):
        issues = list(
            client.pages("github", "/issues", "", {"state": "open", "labels": label})
        )
        for issue in issues:
            if issue.get("pull_request"):
                continue
            state = state_comment(client, issue["number"])
            if not state:
                continue
            _, record = state
            expected = "validate" if label == "jules:validating" else "fix"
            if record["kind"] != expected:
                # Recover if the previous run recorded the fix session but failed
                # before it could finish changing the issue's labels.
                if expected == "validate" and record["kind"] == "fix":
                    add_label(client, issue["number"], "jules:fixing")
                    remove_label(client, issue["number"], "jules:validating")
                continue
            session = client.jules("GET", "/" + record["session"])
            if session.get("state") not in TERMINAL:
                continue
            message = final_message(client, record["session"])
            if expected == "validate":
                finish_validation(client, issue, session, message)
            else:
                finish_fix(client, issue, session, message)


def main():
    required = (
        "GITHUB_REPOSITORY",
        "GITHUB_TOKEN",
        "JULES_API_KEY",
        "GITHUB_EVENT_NAME",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ApiError("Missing required environment variables: " + ", ".join(missing))
    client = Client(
        os.environ["GITHUB_REPOSITORY"],
        os.environ["GITHUB_TOKEN"],
        os.environ["JULES_API_KEY"],
    )
    event_name = os.environ["GITHUB_EVENT_NAME"]
    if event_name in {"schedule", "workflow_dispatch"}:
        poll(client)
    else:
        with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as event_file:
            handle_event(client, event_name, json.load(event_file))


if __name__ == "__main__":
    try:
        main()
    except ApiError as error:
        print(f"Jules issue automation failed: {error}", file=sys.stderr)
        sys.exit(1)
