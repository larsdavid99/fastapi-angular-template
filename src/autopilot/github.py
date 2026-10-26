"""GitHub state, read through the `gh` CLI. The only place that talks to GitHub.

REST only: GitHub refuses GraphQL from a routine.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Callable

from check import Check
from issue import Issue
from pull_request import PullRequest
from ticket_outcome import TicketOutcome

REPO = "repos/{owner}/{repo}"  # gh fills these in from the clone's remote

GhRunner = Callable[[list[str]], Any]
"""Runs `gh` with these arguments and returns its JSON output."""


def run_gh(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


class GitHub:
    def __init__(self, gh: GhRunner):
        self._gh = gh

    def issue(self, number: int) -> Issue:
        return Issue.from_json(self._gh(["api", f"{REPO}/issues/{number}"]))

    def parent(self, number: int) -> Issue:
        """The Spec a Ticket is a sub-issue of. `gh` fails if it has none."""
        return Issue.from_json(self._gh(["api", f"{REPO}/issues/{number}/parent"]))

    def sub_issues(self, number: int) -> list[Issue]:
        """Open and closed, in sub-issue order."""
        return [Issue.from_json(i) for i in self._sub_issues(number)]

    def ticket_outcomes(self, spec_number: int) -> list[TicketOutcome]:
        """In sub-issue order."""
        return [
            TicketOutcome.from_json(
                t, self._list(f"{REPO}/issues/{t['number']}/timeline?per_page=100")
            )
            for t in self._sub_issues(spec_number)
        ]

    def open_issues_labelled(self, label: str) -> list[Issue]:
        """Open issues only: the issues endpoint also returns pull requests."""
        found = self._list(f"{REPO}/issues?labels={label}&state=open&per_page=100")
        return [Issue.from_json(i) for i in found if "pull_request" not in i]

    def was_ever_labelled(self, number: int, label: str) -> bool:
        events = self._list(f"{REPO}/issues/{number}/events?per_page=100")
        return any(
            event["event"] == "labeled" and event["label"]["name"] == label
            for event in events
        )

    def pull_request(self, number: int) -> PullRequest:
        return PullRequest.from_json(self._gh(["api", f"{REPO}/pulls/{number}"]))

    def changed_paths(self, pr_number: int) -> list[str]:
        """A renamed file counts at both paths: moving an ADR away changes it."""
        files = self._list(f"{REPO}/pulls/{pr_number}/files?per_page=100")
        paths = [f["filename"] for f in files]
        return paths + [
            f["previous_filename"] for f in files if "previous_filename" in f
        ]

    def required_checks(self, branch: str) -> list[str]:
        """What the branch's rulesets require to pass before a PR may merge."""
        rules = self._list(f"{REPO}/rules/branches/{branch}?per_page=100")
        return [
            check["context"]
            for rule in rules
            if rule["type"] == "required_status_checks"
            for check in rule["parameters"]["required_status_checks"]
        ]

    def checks(self, sha: str) -> list[Check]:
        """The latest run of each check on a commit, from GitHub Actions or any app."""
        pages = self._gh(
            [
                "api",
                "--paginate",
                "--slurp",
                f"{REPO}/commits/{sha}/check-runs?per_page=100",
            ]
        )
        return [Check.from_json(run) for page in pages for run in page["check_runs"]]

    def _sub_issues(self, number: int) -> list[Any]:
        """GitHub caps a parent at 100."""
        return self._list(f"{REPO}/issues/{number}/sub_issues?per_page=100")

    def _list(self, path: str) -> list[Any]:
        pages = self._gh(["api", "--paginate", "--slurp", path])
        return [item for page in pages for item in page]
