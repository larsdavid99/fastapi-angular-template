"""The `autopilot` command: reads GitHub through `gh` and prints one decision.

    python3 src/autopilot/autopilot.py start <spec>
    python3 src/autopilot/autopilot.py next <spec>
    python3 src/autopilot/autopilot.py branch <ticket> [<path> ...]
    python3 src/autopilot/autopilot.py gate <pr> [--unresolved-spec-finding]
    python3 src/autopilot/autopilot.py merged <pr>
    python3 src/autopilot/autopilot.py summary <spec>

Agents run it and follow what it prints (docs/adr/0001-autopilot-on-cloud-routines.md).
"""

from __future__ import annotations

import argparse
import sys
import time

from branch import decide_branch
from gate import decide_gate
from github import GhRunner, GitHub, run_gh
from merged import Sleep, decide_merged
from next_ticket import decide_next
from start import decide_start
from summary import decide_summary


def main(
    argv: list[str],
    gh: GhRunner = run_gh,
    sleep: Sleep = time.sleep,
) -> None:
    args = _parser(sleep).parse_args(argv)
    print(args.decide(GitHub(gh), args))


def _parser(sleep: Sleep) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autopilot")
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser(
        "start", help="start / resume / wait: <why> / refuse: <reason>"
    )
    start.add_argument("number", type=int, metavar="spec")
    start.set_defaults(decide=lambda github, a: decide_start(github, a.number))

    next_ = commands.add_parser("next", help="ticket #<n> / pause: <why> / done")
    next_.add_argument("number", type=int, metavar="spec")
    next_.set_defaults(decide=lambda github, a: decide_next(github, a.number))

    branch = commands.add_parser("branch", help="claude/<type>/<n>-<slug>")
    branch.add_argument("number", type=int, metavar="ticket")
    branch.add_argument("paths", nargs="*", help="paths the Ticket should touch")
    branch.set_defaults(
        decide=lambda github, a: decide_branch(github, a.number, a.paths)
    )

    gate = commands.add_parser(
        "gate",
        help="auto-merge / request-driver: / request-reviewer: / hand-back:"
        " <reason>",
    )
    gate.add_argument("number", type=int, metavar="pr")
    gate.add_argument(
        "--unresolved-spec-finding",
        action="store_true",
        help="the fixer reported a Spec finding it couldn't resolve",
    )
    gate.set_defaults(
        decide=lambda github, a: decide_gate(
            github, a.number, a.unresolved_spec_finding
        )
    )

    merged = commands.add_parser(
        "merged",
        help="move-on #<spec> / stop: / already-stopped: / wait: / hand-back: / ignore:",
    )
    merged.add_argument("number", type=int, metavar="pr")
    merged.set_defaults(decide=lambda github, a: decide_merged(github, a.number, sleep))

    summary = commands.add_parser("summary", help="the merged PRs, one per Ticket")
    summary.add_argument("number", type=int, metavar="spec")
    summary.set_defaults(decide=lambda github, a: decide_summary(github, a.number))
    return parser


if __name__ == "__main__":
    main(sys.argv[1:])
