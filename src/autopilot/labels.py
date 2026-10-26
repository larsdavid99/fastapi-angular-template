"""The labels Autopilot reads (CONTRIBUTING.md, docs/agents/triage-labels.md)."""

AUTOPILOT = "autopilot"  # Spec: on autopilot
AUTO_MERGE = "autopilot:auto-merge"  # Spec: PRs merge without a person
WORKING = "autopilot:working"  # Ticket: claimed by the loop
MERGE = "autopilot:merge"  # PR: the merge workflow merges it
NEEDS_REVIEW = "needs-review"
READY_FOR_AGENT = "ready-for-agent"
READY_FOR_HUMAN = "ready-for-human"
BUG = "bug"
DOCUMENTATION = "documentation"
