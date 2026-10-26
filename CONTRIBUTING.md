# Contributing

This project is built with Claude Code and the [mattpocock skills](https://github.com/mattpocock/skills). Most of the work is done by agents. People make the decisions, review specs and merge.

This guide covers setup, the roles, and the path an idea takes from a GitHub issue to merged code.

## Setup

1. **Run the app.** Follow the quick start in [`README.md`](README.md#quick-start) (Docker Compose).
2. **GitHub CLI.** Install `gh` and run `gh auth login`. The skills read and write issues through it.
3. **Claude Code + skills.** Install [Claude Code](https://claude.com/claude-code), then inside it:

   ```
   /plugin install mattpocock-skills@claude-plugins-official
   ```

   Skills are invoked as `/mattpocock-skills:<name>` (e.g. `/mattpocock-skills:grill-with-docs`). The short form `/grill-with-docs` works when nothing else has the same name.

4. **Don't re-run `/setup-matt-pocock-skills`.** It has already been run and its output is committed:
   - [`docs/agents/issue-tracker.md`](docs/agents/issue-tracker.md): issues live in this repo's GitHub Issues
   - [`docs/agents/triage-labels.md`](docs/agents/triage-labels.md): the labels below
   - [`docs/agents/domain.md`](docs/agents/domain.md): `GLOSSARY.md` and `docs/adr/`

   Change these files by editing them in a PR, like any other file.

> **Reviewing without Claude:** setup is optional for a Reviewer. Every Reviewer step below can be done in GitHub alone, by reading, commenting and labelling.

Before writing code, read [`GLOSSARY.md`](GLOSSARY.md), [`docs/adr/`](docs/adr) and [`.claude/CLAUDE.md`](.claude/CLAUDE.md) (layering rules). Agents read them too. When an issue, test or PR names a domain concept, use the glossary's word for it.

## Roles

| Role | Default | Does |
|---|---|---|
| **Driver** | The repo owner | Grills the idea, writes the spec, cuts tickets, implements, merges |
| **Reviewer** | The other collaborator, if there is one | Approves every spec, reviews PRs that change the domain model or are requested |

Either of you can raise an idea or take either role. The roles name what you're doing, not who you are. Working alone, you're both: approve your own specs, and Autopilot sends what it would have sent the Reviewer to you.

## Labels

| Label | On | Meaning | Next step |
|---|---|---|---|
| `idea` | Issue | A pitch, not yet discussed | Driver grills it |
| `needs-info` | Idea / spec | Waiting on an answer from the assignee | Assignee replies in a comment, removes the label |
| `needs-review` | Spec | Waiting on the Reviewer's approval | Reviewer approves or requests changes |
| `ready-for-agent` | Ticket (and approved spec) | Fully specified; an agent can build it | Driver runs `/implement` |
| `ready-for-human` | Ticket | Needs a person (judgement, credentials, hardware) | Whoever picks it up |
| `wontfix` | Any | Won't be done | Close |
| `autopilot` | Spec | On [Autopilot](#autopilot): agents build its Tickets one at a time | Remove it to stop after the current Ticket |
| `autopilot:auto-merge` | Spec | Its Autopilot PRs merge themselves once CI is green, unless a gate stops them | None: add or remove it whenever you like |
| `autopilot:working` | Ticket | Autopilot is building it | None: the loop takes it off |
| `autopilot:merge` | PR | The gate let it merge: the merge workflow merges it | None: the loop adds it |

The **assignee** is always the person the issue is waiting on. If an issue is assigned to you, the next move is yours.

## The workflow

```
idea ─► grill ─► spec ─► Reviewer ─► tickets ─► implement ─► PR ─► review ─► merge
issue   Driver   issue   approves    ready-for-   /implement   /pr   /code-
`idea`           `needs-review`       agent                         review
```

### 1. Raise an idea

Open an issue with the `idea` label. A few sentences on the problem is enough. Proposing a solution is optional. You don't need Claude for this, so it's how the Reviewer pitches something without having to drive it.

### 2. Grill it

The Driver runs:

```
/mattpocock-skills:grill-with-docs #<idea>
```

The agent asks questions in rounds until every decision has been made. As terms and trade-offs get settled, it updates `GLOSSARY.md` and writes ADRs. Work on a `docs/<slug>` branch so those edits can be reviewed with the spec.

How to discuss it with the Reviewer depends on the idea:

- **Big or contested ideas: grill together.** Get on a call, the Driver shares their screen, and you both answer the rounds. This is the fastest way to agree.
- **Smaller ideas: grill alone, asynchronously.** When a question needs the other person's view, post it on the idea issue, add `needs-info` and assign them. They answer in a comment. Resume the grilling with their answer.

**Stopping halfway.** If a grilling has to pause before step 3 (to wait on a `needs-info` answer, or to pass it to the other person to drive), run:

```
/mattpocock-skills:handoff continue grilling #<idea>
```

`/handoff` writes the open questions and the decisions so far to a local temp file. Paste it as a comment on the idea issue, so the next session (yours or the Reviewer's) can start from it. For pausing your own work, keeping the file locally is enough.

### 3. Write the spec

At the end of the grilling:

```
/mattpocock-skills:to-spec
```

This publishes a spec issue. Then:

- label it `needs-review` (not `ready-for-agent`) and assign the Reviewer
- open the `docs/<slug>` PR with the glossary/ADR changes and link it from the spec
- close the `idea` issue with a link to the spec

### 4. Reviewer approves the spec

**This gate always applies.** The spec is where the shared decisions live, so both of you sign off on it.

The Reviewer reads the spec and the docs PR. Optionally, they can run `/mattpocock-skills:grill-with-docs #<spec>` to have an agent question them about it. Then they either:

- **approve**: comment "Approved", remove `needs-review`, add `ready-for-agent`, and assign it back to the Driver
- **request changes**: comment what needs to change and assign it back to the Driver. The Driver folds the changes in (re-running `/to-spec` if they're large) and assigns it to the Reviewer again.

On approval, the Driver merges the docs PR.

### 5. Cut tickets

```
/mattpocock-skills:to-tickets #<spec>
```

The agent proposes vertical-slice tickets with their blockers and iterates with the Driver until the breakdown is approved. It then publishes them as sub-issues of the spec, labelled `ready-for-agent`. Tickets only exist for approved specs.

### 6. Implement

For each unblocked ticket:

1. Claim it: `gh issue edit <n> --add-assignee @me`.
2. Work in a fresh worktree, so several tickets can run in parallel:

   ```bash
   git worktree add ../<repo>-<n> -b feature/<n>-<slug> main
   ```

   Branches are `<type>/<n>-<slug>`, with type `feature`, `fix`, `docs`, `chore` or `ci`. [Autopilot](#autopilot)'s branches are `claude/<type>/<n>-<slug>`, so never start a branch of your own with `claude/`: Autopilot reviews every PR whose branch does.

3. In Claude Code, inside that worktree:

   ```
   /mattpocock-skills:implement #<n>
   ```

   The agent works test-first and commits to the branch. Check that every check in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) passes locally (see [`README.md`](README.md#development)). CI runs the same checks on the PR.

4. Push, then write the PR with:

   ```
   /mattpocock-skills:pr
   ```

   The body must start with `Closes #<n>`, so the ticket closes on merge, and must have a **Review order** section (see [Review order](#review-order)). `/pr` doesn't write that section unprompted, so ask for it.

To build a whole spec in one go, `/mattpocock-skills:implement-spec #<spec>` runs one agent per ticket on an integration branch. To have agents build it one ticket at a time while you're away, put it on [Autopilot](#autopilot).

### 7. Review and merge

On the PR branch (`gh pr checkout <pr>`):

```
/mattpocock-skills:code-review main
```

Use the **mattpocock** `code-review`, not Claude Code's built-in `/code-review`. It reports on two axes:

- **Standards**: does the code follow `.claude/CLAUDE.md`?
- **Spec**: does it do what the linked ticket asked?

Post the report as a PR comment, fix the findings in `Address review: …` commits, and merge.

**When the Reviewer reviews a PR:** the Driver reviews and merges their own PRs. Request the Reviewer (and wait for their approval) when a PR:

- changes `GLOSSARY.md` or an ADR, or
- strays from the approved spec, or
- you just want a second pair of eyes.

`main` doesn't require an approving review, so the Driver isn't blocked on routine work.

## Review order

Agents write most of the code, so a person has to be able to understand a PR without having built it. Every PR body has a **Review order** section: the changed files, in the order a reviewer should read them, with one line each on what to look for.

Build it in four parts:

1. **Docs.** The ticket and its spec stories, then any changes to ADRs, `GLOSSARY.md`, `docs/architecture-pattern.md` or `.claude/CLAUDE.md`. This is what was asked for and what was decided.
2. **Setup.** `env_config.py`, `.env.example`, `docker-compose.yml`, `requirements*.txt`, `package.json`, and test harness changes (`conftest.py`). These are the new switches, defaults and dependencies.
3. **One block per vertical slice.** Start each block with its test, because the test states what the slice promises. Then list the code bottom-up, the order it was built in:

   ```
   backend:  Resource Access / Client → DTOs → Logic → Facade → Dependencies → Router → main.py
   frontend: models → data services → logic services → pages / components
   ```

4. **Follow-ups.** The issues opened for what the PR deliberately leaves out.

Rules:

- **Files, not commits.** `Address review: …` commits rewrite earlier ones, so a per-commit read shows code that no longer exists.
- **Mark the riskiest slice.** Point out anything that sends data off our infrastructure, deletes data irreversibly or changes a privacy boundary, and say what to check there.
- **Give rough minutes per block**, so the Reviewer can plan the session.
- **More than three slices means the PR is too big.** Split it instead.

Example:

```markdown
## Review order

**1. Docs (10 min)**
- #15 and stories 4–6 in #2: what was asked
- `docs/adr/0002-orders-expire.md`: why orders expire after 30 days

**2. Setup (5 min)**
- `src/backend/env_config.py`: `ORDER_TTL_DAYS`, 30 by default
- `src/backend/tests/conftest.py`: a fixed clock for the expiry tests

**3. Slice: expiring orders (20 min)** ⚠️ deletes data irreversibly
- `tests/test_order_expiry_logic.py`: 31-day-old orders go, 29-day-old orders stay
- `resource_access/order_repository.py`: `delete_before`, no commit
- `logic/order_expiry_logic.py`: the cutoff rule
- `facade/order_expiry_facade.py`: one transaction, committed here
- `router/order_router.py`: `POST /api/orders/expire`

**4. Follow-ups**
- #27: show expired orders in the UI
```

To read one file's diff locally: `git diff main...<branch> -- <path>`. On GitHub, use the file filter in "Files changed".

## The fast lane

A change skips steps 1–5 and goes straight to a ticket when **both** are true:

- it adds no new glossary term and no ADR, and
- it fits in one ticket.

Bugs, chores and small tweaks usually qualify. Open the ticket directly (or ask `/mattpocock-skills:triage` to write it up) with `ready-for-agent`, then continue from step 6. If you find out during the work that it needs a new term or a real trade-off, stop and turn it into an `idea`.

## Autopilot

Autopilot builds an approved Spec one Ticket at a time, with no one at the keyboard ([ADR-0001](docs/adr/0001-autopilot-on-cloud-routines.md)). It replaces steps 6 and 7 for that Spec. Steps 1 to 5 are still yours.

It runs as two Claude Code cloud routines on the Driver's account, so everything it does on GitHub shows as the Driver. Their instructions are [`docs/agents/autopilot-implement.md`](docs/agents/autopilot-implement.md) and [`docs/agents/autopilot-review.md`](docs/agents/autopilot-review.md). The agents write, review and fix the code, but they never decide what happens next. The `autopilot` command in [`src/autopilot/`](src/autopilot) does, and the agents do what it prints. Both routines run in one cloud environment, set up on claude.ai. Its setup script and the routines' triggers and prompts are recorded in [the Implement instructions](docs/agents/autopilot-implement.md#the-cloud-environment).

### Setting up Autopilot

A repo made from this template has the code, the workflows and the hook already. Neither GitHub's settings nor claude.ai's come with it, so set these up once per repo:

1. **Labels and ruleset.** From a clone, with `gh auth login` done:

   ```bash
   ./bin/setup-autopilot.sh
   ```

   It creates the [labels](#labels) and a ruleset on `main`: PRs only, conversations resolved, every CI check required, no approval needed. It's safe to run again, for example after you add a check to `.github/workflows/ci.yml` and to the script's list. The gate hands back every PR while `main` requires no checks.

2. **Sub-issues and dependencies.** Autopilot reads a Spec's Tickets as GitHub sub-issues, and their blockers as issue dependencies. Both are on by default on GitHub.com.
3. **The cloud environment.** On [claude.ai/code](https://claude.ai/code), connect the repo and create a cloud environment named after it (for example `my-app-autopilot`), with Limited network and the setup script recorded in [the Implement instructions](docs/agents/autopilot-implement.md#the-cloud-environment).
4. **The routines.** Create `autopilot-implement` and `autopilot-review` in that environment, with the triggers and prompts in the same section's table. Set each one's model to Opus 5.5, and turn notifications on.
5. **The start workflow's secrets.** Add an API trigger to `autopilot-implement`, and store its URL and token as repo secrets:

   ```bash
   gh secret set AUTOPILOT_IMPLEMENT_FIRE_URL
   gh secret set AUTOPILOT_IMPLEMENT_FIRE_TOKEN
   ```

6. **Try it.** Put a small Spec with one docs-only Ticket on autopilot, and watch the Spec's comments.

If you change any of this on claude.ai later, change [the Implement instructions](docs/agents/autopilot-implement.md#the-cloud-environment) to match in the same go.

### The loop

1. **Implement.** A fresh agent picks the next Ticket: the first open sub-issue of the Spec, in order, that has no open blocker and isn't `ready-for-human` or `autopilot:working`. It labels the Ticket `autopilot:working` (nobody is assigned), builds it test-first on a `claude/<type>/<n>-<slug>` branch, runs every check CI runs, reviews it with the mattpocock `code-review`, and opens a PR that starts with `Closes #<n>` and has a [Review order](#review-order).
2. **Review.** When the PR opens, a fresh agent runs the mattpocock `code-review` and posts the report as one PR comment. A fresh fixer agent fixes the findings in `Address review: …` commits and replies to each one. There is exactly one review round.
3. **Gate.** Once CI has finished, the `autopilot gate` command decides what happens to the PR (see [Gates](#gates)). A PR comment says which gate it chose and why.
4. **Merge.** When the PR merges, a fresh agent starts the next Ticket.

The mattpocock skills run on every Ticket and PR, however small: `tdd` for a Ticket that changes `src/`, `code-review` before the PR opens and again in Review, and `pr` for the PR's title and body. A hook in `.claude/settings.json` ([`src/autopilot/skills_hook.py`](src/autopilot/skills_hook.py)) checks this from each run's transcript. It refuses to open an Implement run's PR, or post a Review run's first comment, until the skills have run. If a run still got past that, the hook sends it back before it stops.

### Start, stop and resume

- **Start:** add `autopilot` to a Spec that's `ready-for-agent`. To let its PRs merge themselves, add `autopilot:auto-merge` as well. Autopilot refuses the Spec, takes the label off and says why if it still has `needs-review`, isn't `ready-for-agent` or has no Tickets, or if another Spec is already on autopilot.
- **Stop:** remove `autopilot`. The Ticket being built carries on to its PR. When that PR merges, Autopilot says on the Spec that it stopped, and starts nothing else.
- **Resume:** add `autopilot` again. Autopilot carries on from the next unblocked Ticket. If a Ticket is still being built, it waits for that PR to merge.
- **Pause:** when only blocked or `ready-for-human` Tickets are left, Autopilot takes `autopilot` off, says on the Spec what it's waiting on, and assigns the Spec to the Driver. It doesn't restart when that Ticket closes. Add `autopilot` again.

`autopilot:auto-merge` is read each time a PR is gated, so adding or removing it changes every PR gated after that.

### Reading the loop

- **The Spec** gets a comment each time Autopilot starts, resumes, moves on, pauses, stops or finishes.
- **The Ticket being built** has `autopilot:working`.
- **Each PR** has the review report, the fixer's reply to every finding, and an `Autopilot gate: …` comment.
- **The assignee** is still who it's waiting on. If Autopilot assigned you something, the next move is yours.
- **The Claude app** sends you a push notification when each run ends, whatever the outcome, so allow its notifications on your phone. GitHub doesn't notify you, because Autopilot acts as you.

### Gates

The gate is checked in this order, and the first one that applies wins:

| Gate | When | What happens |
|---|---|---|
| `hand-back` | A required check is red, unfinished or missing, `main` requires no checks, or the PR conflicts with `main` (or GitHub hasn't said yet whether it does) | The Ticket goes back to the Driver, and the loop stops (see [Failures](#failures)) |
| `request-reviewer` | The PR changes `GLOSSARY.md` or an ADR, or the fixer couldn't resolve a Spec finding | The Reviewer's review is requested. If the repo doesn't have exactly one other collaborator, it waits for the Driver instead |
| `request-driver` | The PR changes the loop's own machinery: `.github/`, `.claude/`, `docs/agents/autopilot-*` or `src/autopilot/` | The PR is assigned to the Driver |
| `request-driver` | The Spec isn't labelled `autopilot:auto-merge` | The PR is assigned to the Driver |
| `auto-merge` | Anything else | The PR is labelled `autopilot:merge`, and the merge workflow ([`autopilot-merge.yml`](.github/workflows/autopilot-merge.yml)) merges it with a merge commit, once it has checked the gate for itself. It then closes the Ticket itself: GitHub ignores `Closes #<n>` when a workflow's token merges a PR |

The first three rows always stop for a person, whatever the labels say. A person reviews a waiting PR as in [step 7](#7-review-and-merge) and merges it, and the merge carries the loop on.

GitHub doesn't let the author of a PR request their own review, and the Driver authors every Autopilot PR. So a PR waiting on the Driver is assigned to them instead.

### Failures

Any failure stops the whole loop, because later Tickets usually build on the one that failed. Failures include checks that won't go green, CI that's still red after the fixes, a merge conflict, a PR the merge workflow won't merge, and a Ticket too underspecified to build without guessing.

Autopilot then hands the Ticket back: it takes `autopilot:working` off, labels it `ready-for-human`, assigns it to the Driver, and comments what failed and where the branch is. It takes `autopilot` off the Spec and says so there.

To carry on, finish the Ticket yourself. Take over the branch and its PR, or build it by hand. Once it's merged, add `autopilot` again.

### Finishing a Spec

When every Ticket is closed, Autopilot removes `autopilot` and `autopilot:auto-merge`, comments the list of merged PRs on the Spec, and assigns it to the Driver. Autopilot doesn't close the Spec. Check that every story is covered, then close it.

## Other skills worth knowing

| Skill | When |
|---|---|
| `diagnosing-bugs` | Something is broken or slow and the cause isn't obvious |
| `tdd` | Building by hand, test-first |
| `prototype` | A throwaway to answer a design question before speccing |
| `research` | Gathering facts from primary docs into a Markdown file |
| `triage` | Turning a raw issue into a ticket with an agent brief |
