"""`gate <pr>`: what happens to an Autopilot PR once it's reviewed and CI is done."""

from __future__ import annotations

from branch import ticket_of
from check import Check
from github import GitHub
from labels import AUTO_MERGE
from pull_request import PullRequest

# Shared decisions: only the Reviewer may let these through.
_DOMAIN_MODEL = ("GLOSSARY.md", "docs/adr/")

# The loop's own rules: an agent mustn't change what checks it without the Driver.
_MACHINERY = (".github/", ".claude/", "docs/agents/autopilot-", "src/autopilot/")


def decide_gate(github: GitHub, pr_number: int, unresolved_spec_finding: bool) -> str:
    pr = github.pull_request(pr_number)
    ticket_number = _ticket_built_by(pr)
    conflict = _conflict(pr)
    if conflict:
        return f"hand-back: {conflict}"
    red = _red_ci(github.required_checks(pr.base), github.checks(pr.head_sha))
    if red:
        return f"hand-back: {red}"
    paths = github.changed_paths(pr_number)
    for_reviewer = _for_reviewer(paths, unresolved_spec_finding)
    if for_reviewer:
        return f"request-reviewer: {for_reviewer}"
    machinery = _touched(paths, _MACHINERY)
    if machinery:
        return f"request-driver: changes {_listed(machinery)}"
    spec = github.parent(ticket_number)
    if AUTO_MERGE not in spec.labels:
        return f"request-driver: #{spec.number} isn't labelled {AUTO_MERGE}"
    return "auto-merge"


def _ticket_built_by(pr: PullRequest) -> int:
    """Hand-written PRs are the Driver's own, so the loop never acts on them."""
    ticket_number = ticket_of(pr.branch)
    if ticket_number is None:
        raise SystemExit(f"#{pr.number} isn't an Autopilot PR: {pr.branch}")
    return ticket_number


def _conflict(pr: PullRequest) -> str | None:
    """Before red CI: GitHub runs no CI on a conflicting PR.

    Unknown counts too, since green checks can predate a conflict.
    """
    if pr.mergeable is None:
        return f"GitHub hasn't said whether it conflicts with {pr.base}"
    if not pr.mergeable:
        return f"conflicts with {pr.base}"
    return None


def _red_ci(required: list[str], checks: list[Check]) -> str | None:
    """Only the checks the base branch requires: the ones GitHub's merge waits for."""
    # Without them, nothing stands between an agent's code and main.
    if not required:
        return "main requires no CI checks"
    by_name = {check.name: check for check in checks}
    ran = [by_name[name] for name in required if name in by_name]
    failed = [c.name for c in ran if c.finished and not c.passed]
    if failed:
        return f"CI is red: {_listed(failed)}"
    running = [c.name for c in ran if not c.finished]
    if running:
        return f"CI hasn't finished: {_listed(running)}"
    missing = [name for name in required if name not in by_name]
    if missing:
        return f"CI didn't run: {_listed(missing)}"
    return None


def _for_reviewer(paths: list[str], unresolved_spec_finding: bool) -> str | None:
    """Both reasons when both hold, so the Reviewer knows what to look at."""
    reasons = []
    domain = _touched(paths, _DOMAIN_MODEL)
    if domain:
        reasons.append(f"changes {_listed(domain)}")
    if unresolved_spec_finding:
        reasons.append("the fixer couldn't resolve a Spec finding")
    return "; ".join(reasons) or None


def _touched(paths: list[str], prefixes: tuple[str, ...]) -> list[str]:
    return [path for path in paths if path.startswith(prefixes)]


def _listed(names: list[str]) -> str:
    """Sorted, so the same PR gets the same reason on every run."""
    return ", ".join(sorted(names))
