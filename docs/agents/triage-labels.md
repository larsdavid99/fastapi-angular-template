# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

Edit the "Label in our tracker" column to match whatever vocabulary you actually use.

## Repo-specific labels and overrides

The full workflow is in `CONTRIBUTING.md`. These rules override the skills' defaults:

| Label                  | Meaning                                                                     |
| ---------------------- | --------------------------------------------------------------------------- |
| `idea`                 | A pitch not yet grilled. Input to `/grill-with-docs`, not work              |
| `needs-review`         | A spec waiting on the Reviewer's approval                                   |
| `autopilot`            | A Spec on Autopilot: agents build its Tickets one at a time                 |
| `autopilot:auto-merge` | A Spec whose Autopilot PRs merge once CI is green, unless a gate stops them |
| `autopilot:working`    | A Ticket Autopilot is building                                              |
| `autopilot:merge`      | A PR the gate let merge: the merge workflow merges it with a merge commit   |

- **Specs start in `needs-review`.** When `/to-spec` publishes a spec, apply `needs-review` instead of `ready-for-agent`, and assign the other contributor. The Reviewer swaps it to `ready-for-agent` on approval.
- **No tickets for unapproved specs.** `/to-tickets` must refuse a spec that still has `needs-review`, and tell the user to wait for approval.
- **The assignee is who the issue is waiting on.** When you hand an issue to someone (`needs-info`, `needs-review`), reassign it to them.
- **Autopilot's labels are the Driver's and the loop's.** The Driver adds and removes `autopilot` and `autopilot:auto-merge`, and Autopilot takes them off when it stops, pauses or finishes. Never claim, assign or build a Ticket labelled `autopilot:working`. Only Autopilot's Review run adds `autopilot:merge`, and the merge workflow checks the gate again before it merges. See Autopilot in `CONTRIBUTING.md`.
- **`claude/` branches are Autopilot's.** Its branches are `claude/<type>/<n>-<slug>`, beside the hand-written `<type>/<n>-<slug>`. Never start a branch with `claude/` unless you're Autopilot: it reviews every PR whose branch does.
- **Never implement an `idea`.** It needs grilling and a spec first, unless the user explicitly sends it down the fast lane (see `CONTRIBUTING.md`).
