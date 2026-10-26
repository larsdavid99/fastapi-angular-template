#!/usr/bin/env bash
# setup-autopilot.sh — the GitHub side of Autopilot for a repo made from this template.
#
# Usage: ./bin/setup-autopilot.sh   (from a clone, with `gh auth login` done)
#
# Creates or updates:
#   - the workflow labels (CONTRIBUTING.md, Labels)
#   - the "Main Ruleset" on the default branch: PRs only, conversations resolved,
#     every CI check required, no approval needed
#
# Safe to run again. The claude.ai side (cloud environment, routines, the two
# AUTOPILOT_IMPLEMENT_FIRE_* secrets) is set up by hand: see CONTRIBUTING.md,
# Setting up Autopilot.
set -euo pipefail

# The check names CI reports: keep in step with the job names in .github/workflows/ci.yml.
REQUIRED_CHECKS=(
    "pytest"
    "black"
    "flake8"
    "frontend build"
    "autopilot pytest"
    "autopilot pytest (3.9)"
    "autopilot black"
    "autopilot flake8"
    "autopilot mypy"
)
RULESET_NAME="Main Ruleset"
GITHUB_ACTIONS_APP_ID=15368  # so only GitHub Actions can report a required check

label() {
    gh label create "$1" --color "$2" --description "$3" --force >/dev/null
    echo "label: $1"
}

label "needs-triage" fbca04 "Maintainer needs to evaluate this issue"
label "needs-info" d876e3 "Waiting on reporter for more information"
label "ready-for-agent" 0e8a16 "Fully specified, ready for an AFK agent"
label "ready-for-human" 1d76db "Requires human implementation"
label "wontfix" ffffff "This will not be worked on"
label "idea" c5def5 "A pitch, not yet grilled"
label "needs-review" fbca04 "Spec waiting on the Reviewer's approval"
label "autopilot" 5319e7 "Spec is on autopilot"
label "autopilot:auto-merge" 5319e7 "Autopilot PRs merge without human review"
label "autopilot:working" c5def5 "Ticket claimed by Autopilot"
label "autopilot:merge" c5def5 "PR the gate let merge; the merge workflow merges it"

checks_json=$(printf '%s\n' "${REQUIRED_CHECKS[@]}" \
    | python3 -c 'import json, sys; print(json.dumps([{"context": c, "integration_id": int(sys.argv[1])} for c in sys.stdin.read().splitlines()]))' "$GITHUB_ACTIONS_APP_ID")

# Admins may bypass it only through a PR. Merge commits stay allowed: the
# Autopilot merge workflow merges with one.
ruleset=$(cat <<EOF
{
  "name": "$RULESET_NAME",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}],
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "pull_request", "parameters": {
      "allowed_merge_methods": ["merge", "squash", "rebase"],
      "dismiss_stale_reviews_on_push": false,
      "require_code_owner_review": false,
      "require_last_push_approval": false,
      "required_approving_review_count": 0,
      "required_review_thread_resolution": true
    }},
    {"type": "required_status_checks", "parameters": {
      "do_not_enforce_on_create": false,
      "strict_required_status_checks_policy": false,
      "required_status_checks": $checks_json
    }}
  ]
}
EOF
)

existing=$(gh api "repos/{owner}/{repo}/rulesets" -q ".[] | select(.name == \"$RULESET_NAME\") | .id")
if [[ -n "$existing" ]]; then
    echo "$ruleset" | gh api -X PUT "repos/{owner}/{repo}/rulesets/$existing" --input - --silent
    echo "ruleset: updated $RULESET_NAME"
else
    echo "$ruleset" | gh api -X POST "repos/{owner}/{repo}/rulesets" --input - --silent
    echo "ruleset: created $RULESET_NAME"
fi

echo "Done. Next: the claude.ai side, in CONTRIBUTING.md (Setting up Autopilot)."
