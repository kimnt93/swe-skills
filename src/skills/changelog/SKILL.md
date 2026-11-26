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
| **Project** | `<project dir>/changelog/project.md` and `changelog/<repo>.md` | the manager | **after** each merge |

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
change is marked. A missing or wrong entry is a finding (`gh pr diff <pr> -R <owner>/<repo> --name-only` shows whether the
file is touched). A PR that needs an entry and has none does not pass.

## For the manager

- **Before merge**: every ready PR has its changelog entry. A missing one goes back to whoever builds the PR (the
  developer bot or agent), who adds it on the PR's branch with this skill; checks run again and the new head is reviewed
  again under the playbook's rules.
- **After merge**: each merged PR gets one line (date, repo, type, title, PR link) in `changelog/<repo>.md` and
  `changelog/project.md`. As the CTO/CEO you delegate that edit like any other change to a file.
- **The cross-repo story**: when a change spans repos (an API change in `api` and the client update in `web`), add one prose
  line to `changelog/project.md` under the month, linking the PRs: `- Order cancellation: API ([api#41](https://github.com/acme/api/pull/41)), dashboard
  ([web#17](https://github.com/acme/web/pull/17))`. Keep it to what the team needs to know.
- **Cutting a release** of one repo: rename `## [Unreleased]` to `## [x.y.z] - YYYY-MM-DD`, add a fresh empty `## [Unreleased]`,
  tag and release through the `github` skill, and add a line to `changelog/project.md`: `- api 1.4.0 released ([notes](https://github.com/acme/api/releases/tag/v1.4.0))`.
  The version follows the change kinds (breaking: major, `Added`: minor, only `Fixed`: patch).
- **Questions** ("what changed in api this month?"): answer from `changelog/api.md` and the merged pull requests.

## Commands

```bash
gh pr diff <pr> -R <owner>/<repo> --name-only      # is CHANGELOG.md in the pull request
gh pr list -R <owner>/<repo> --state merged --search 'merged:>=2026-11-01'   # what merged since a date
```

## Rules

- **One line per change**, no commit-message dumps, no internal ticket jargon, no secrets or private URLs.
- **The entry ships with the code**: if the PR is reverted, the entry is reverted with it.
- **Never rewrite released sections**; fix a wrong released line with a new entry.
- **Keep the project log append-only** except for the manager's cross-repo lines and release notes.

## Example prompts

- "the changelog entry is missing on api#41" -> manager: send it back to its builder
- "add the changelog entry for this PR" -> PR author steps
- "what did we ship across the repos this month?" -> read the project log, then summarise
