"""GitHub as the `gh` CLI shows it: `gh api` calls answered with REST JSON.

Never GraphQL: GitHub refuses it from a routine.
"""

from __future__ import annotations

import re
import subprocess
from typing import Any

REPO = "repos/{owner}/{repo}"


class FakeGitHub:
    def __init__(self) -> None:
        self._issues: dict[int, dict[str, Any]] = {}
        self._sub_issues: dict[int, list[int]] = {}
        self._events: dict[int, list[dict[str, Any]]] = {}
        self._pulls: dict[int, dict[str, Any]] = {}
        self._files: dict[int, list[dict[str, Any]]] = {}
        self._check_runs: dict[str, list[dict[str, Any]]] = {}
        self._rules: dict[str, list[dict[str, Any]]] = {}
        self._cross_references: dict[int, list[dict[str, Any]]] = {}
        self._closes_on_read: dict[int, int] = {}

    def issue(
        self,
        number: int,
        title: str = "An issue",
        labels: tuple[str, ...] = (),
        state: str = "open",
        open_blockers: int = 0,
    ) -> None:
        self._issues[number] = {
            "number": number,
            "title": title,
            "state": state,
            "labels": [],
            "issue_dependencies_summary": {
                "blocked_by": open_blockers,
                "total_blocked_by": open_blockers,
            },
        }
        self._events[number] = []
        for name in labels:
            self.label(number, name)

    def pull_request(
        self,
        number: int,
        labels: tuple[str, ...] = (),
        branch: str = "feature/1-a-pull-request",
        paths: tuple[str, ...] = (),
        merged: bool = False,
        mergeable: bool | None = True,
    ) -> None:
        """`mergeable` is None while GitHub is still working it out."""
        self.issue(
            number,
            title="A pull request",
            labels=labels,
            state="closed" if merged else "open",
        )
        self._issues[number]["pull_request"] = {"url": f"{REPO}/pulls/{number}"}
        self._pulls[number] = {
            "number": number,
            "head": {"ref": branch, "sha": f"sha-of-{number}"},
            "base": {"ref": "main"},
            "merged": merged,
            "mergeable": mergeable,
        }
        self._files[number] = [
            {"filename": path, "status": "modified"} for path in paths
        ]

    def renamed_file(self, pr: int, old: str, new: str) -> None:
        self._files[pr].append(
            {"filename": new, "previous_filename": old, "status": "renamed"}
        )

    def check_run(
        self,
        pr: int,
        name: str,
        conclusion: str | None = "success",
        status: str = "completed",
    ) -> None:
        """On the PR's head commit. A run that hasn't completed has no conclusion."""
        sha = self._pulls[pr]["head"]["sha"]
        self._check_runs.setdefault(sha, []).append(
            {"name": name, "status": status, "conclusion": conclusion}
        )

    def closed_by(self, ticket: int, pr: int, merged: bool = True) -> None:
        """A PR whose body says `Closes #<ticket>`, merged or closed unmerged."""
        self._cross_reference(ticket, pr, f"Closes #{ticket}\n\n## Summary", merged)

    def mentioned_by(self, ticket: int, pr: int, closes: int) -> None:
        """A merged PR that names the Ticket, but closes another one."""
        body = f"Closes #{closes}. Follows on from #{ticket}."
        self._cross_reference(ticket, pr, body)

    def _cross_reference(
        self, ticket: int, pr: int, body: str, merged: bool = True
    ) -> None:
        """What a Ticket's timeline shows once a PR's body names it."""
        source = {
            "number": pr,
            "body": body,
            "state": "closed",
            "pull_request": {"merged_at": "2026-10-24T15:49:52Z" if merged else None},
        }
        self._cross_references.setdefault(ticket, []).append(
            {"event": "cross-referenced", "source": {"type": "issue", "issue": source}}
        )

    def closes_on_read(self, number: int, nth: int) -> None:
        """Open until it's read for the `nth` time, as the merge workflow closes it."""
        self._closes_on_read[number] = nth

    def label(self, number: int, name: str) -> None:
        self._issues[number]["labels"].append({"name": name})
        self._events[number].append({"event": "labeled", "label": {"name": name}})

    def unlabel(self, number: int, name: str) -> None:
        labels = self._issues[number]["labels"]
        labels.remove({"name": name})
        self._events[number].append({"event": "unlabeled", "label": {"name": name}})

    def required_checks(self, branch: str, *names: str) -> None:
        """The checks a ruleset on the branch requires; none means no such rule."""
        rule = {
            "type": "required_status_checks",
            "parameters": {
                "required_status_checks": [{"context": name} for name in names]
            },
        }
        self._rules[branch] = [{"type": "deletion"}, rule] if names else []

    def sub_issues(self, parent: int, *children: int) -> None:
        """Children in sub-issue order."""
        self._sub_issues[parent] = list(children)

    def __call__(self, args: list[str]) -> Any:
        assert args[0] == "api", f"unexpected gh call: {args}"
        assert args[1] != "graphql", f"GraphQL is blocked in routines: {args}"
        path = args[-1]
        body = self._answer(path)
        if "--slurp" in args:
            return [body]  # one page
        return body

    def _answer(self, path: str) -> Any:
        if m := re.fullmatch(rf"{re.escape(REPO)}/issues/(\d+)", path):
            return self._read_issue(int(m[1]))
        if m := re.fullmatch(rf"{re.escape(REPO)}/issues/(\d+)/sub_issues\?.*", path):
            return [self._issues[n] for n in self._sub_issues.get(int(m[1]), [])]
        if m := re.fullmatch(rf"{re.escape(REPO)}/issues/(\d+)/events\?.*", path):
            return self._events[int(m[1])]
        if m := re.fullmatch(rf"{re.escape(REPO)}/issues/(\d+)/timeline\?.*", path):
            n = int(m[1])
            return self._events[n] + self._cross_references.get(n, [])
        if m := re.fullmatch(rf"{re.escape(REPO)}/issues/(\d+)/parent", path):
            return self._parent(int(m[1]))
        if m := re.fullmatch(rf"{re.escape(REPO)}/rules/branches/([^?]+)\?.*", path):
            return self._rules.get(m[1], [])
        if m := re.fullmatch(rf"{re.escape(REPO)}/pulls/(\d+)", path):
            return self._pulls[int(m[1])]
        if m := re.fullmatch(rf"{re.escape(REPO)}/pulls/(\d+)/files\?.*", path):
            return self._files[int(m[1])]
        if m := re.fullmatch(
            rf"{re.escape(REPO)}/commits/([^/]+)/check-runs\?.*", path
        ):
            runs = self._check_runs.get(m[1], [])
            return {"total_count": len(runs), "check_runs": runs}
        if m := re.fullmatch(
            rf"{re.escape(REPO)}/issues\?labels=([^&]+)&state=open&.*", path
        ):
            return [
                issue
                for issue in self._issues.values()
                if issue["state"] == "open" and {"name": m[1]} in issue["labels"]
            ]
        raise AssertionError(f"unexpected gh api path: {path}")

    def _read_issue(self, number: int) -> dict[str, Any]:
        if number in self._closes_on_read:
            self._closes_on_read[number] -= 1
            if self._closes_on_read[number] == 0:
                self._issues[number]["state"] = "closed"
        return self._issues[number]

    def _parent(self, number: int) -> dict[str, Any]:
        for parent, children in self._sub_issues.items():
            if number in children:
                return self._issues[parent]
        # gh exits non-zero on the 404, as for any other failed call
        raise subprocess.CalledProcessError(1, ["gh", "api"], stderr="Not Found (404)")
