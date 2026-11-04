---
name: changelog
description: Keep change logs true across a project of several GitHub repos - every repo has a CHANGELOG.md with an Unreleased section and every pull request that changes behaviour adds its entry before merge; the manager keeps a project change log directory (changelog/project.md and one file per repo) that records each merged PR and the cross-repo story. Use when opening, reviewing or fixing a PR that needs a change log entry, when the merge gate says the changelog is missing, when cutting a release, or when asked what changed in a repo or in the project.
metadata:
  group: process
  summary: "Change logs: a CHANGELOG.md entry in every PR, plus the project's changelog/ directory"
  version: "1.0"
---

# Change logs

Two layers, each with one owner:

| Layer | Where | Written by | When |
|---|---|---|---|
| **Repo** | `CHANGELOG.md` in each target repo, `## [Unreleased]` section | the PR's author (developer, or the scribe role as a fix) | in the PR, **before merge** |
| **Project** | `<project dir>/changelog/project.md` and `changelog/<repo>.md` | the manager (`swe-cli changelog record`, run by `flow merge`) | **after** each merge |

The repo log tells users and operators what changed in that repo. The project log tells the team what changed across all of
its repos, in one place, newest first, with a link to every PR.

## For the PR author (developer, scribe)

1. Add one line to `## [Unreleased]` in the repo's `CHANGELOG.md` **in the same PR**, under the right heading
   (`Added`, `Changed`, `Fixed`, `Removed`, `Security`). Create the file from [format](references/format.md) if the repo has none.
2. Write for the reader of the release notes, not the diff: what a user or operator can now do or must now do, in the present
   tense, one line, with the PR number: `- Cancel an open order with \`DELETE /v1/orders/{id}\` ([#41](https://github.com/acme/api/pull/41))`.
3. A breaking change starts with `**Breaking:**` and says what to do. A migration or config change names the step.
4. No entry is needed for: `docs`, `chore`, `ci`, `test`, `style`, `build` PRs, or a PR labelled `no-changelog`. Anything that
   changes behaviour, an API, a schema, a message format, a config key or a dependency version users see **does**.
5. Push the change with the code; do not edit `CHANGELOG.md` in a separate PR.

## For the reviewer

Check the PR's diff contains the entry and that it is true: the line matches what the diff does, the heading fits, a breaking
change is marked. A missing or wrong entry is a finding (`swe-cli changelog check <pr> --repo <owner/repo>` says if the file
is touched). The merge gate refuses a PR that needs an entry and has none.

## For the manager

- **Before merge**: `swe-cli flow merge` runs the check for every ready PR. If it says the changelog is missing, start the fix:
  `swe-cli flow run <project> changelog --input pr=<n> --input repo=<repo>`. A scribe adds the entry on the PR's branch, checks
  run again and a reviewer re-reviews the new head; merge that run's PR.
- **After merge**: `flow merge` records every merged PR with `swe-cli changelog record` (date, repo, type, title, PR link) in
  `changelog/<repo>.md` and `changelog/project.md`. You do not write those lines by hand.
- **The cross-repo story**: when a change spans repos (an API change in `api` and the client update in `web`), add one prose
  line to `changelog/project.md` under the month, linking the PRs: `- Order cancellation: API ([api#41](https://github.com/acme/api/pull/41)), dashboard
  ([web#17](https://github.com/acme/web/pull/17))`. Keep it to what the team needs to know.
- **Cutting a release** of one repo: rename `## [Unreleased]` to `## [x.y.z] - YYYY-MM-DD`, add a fresh empty `## [Unreleased]`,
  tag and release through the `github` skill, and add a line to `changelog/project.md`: `- api 1.4.0 released ([notes](https://github.com/acme/api/releases/tag/v1.4.0))`.
  The version follows the change kinds (breaking: major, `Added`: minor, only `Fixed`: patch).
- **Questions** ("what changed in api this month?"): `swe-cli changelog show --repo api --since 2026-11-01`.

## Commands

```bash
swe-cli changelog check <pr> --repo <owner/repo>        # does the PR need an entry, and does it have one
swe-cli changelog record <project> <repo> --pr <n> ...   # append a merged PR to the project's changelog/ (flow merge does this)
swe-cli changelog show [--repo <name>] [--since YYYY-MM-DD]
```

## Rules

- **One line per change**, no commit-message dumps, no internal ticket jargon, no secrets or private URLs.
- **The entry ships with the code**: if the PR is reverted, the entry is reverted with it.
- **Never rewrite released sections**; fix a wrong released line with a new entry.
- **Keep the project log append-only** except for the manager's cross-repo lines and release notes.

## Example prompts

- "the gate says the changelog is missing on api#41" -> manager: start the `changelog` workflow
- "add the changelog entry for this PR" -> PR author steps
- "what did we ship across the repos this month?" -> `changelog show`, then summarise
