---
name: playbook-changelog
description: "Changelog playbook: keep repository changelog accurate across pull requests and releases. Adds missing changelog entries to open PRs, validates formatting, and cuts release notes."
metadata:
  group: start
  summary: "Playbook for changelog: record PR entries and maintain unreleased release notes"
---

# Playbook: Changelog

The changelog playbook maintains an accurate `CHANGELOG.md` following Keep a Changelog standards across all merges.

## Steps

### 1. Check Missing Entries
1. Verify if the target pull request already includes an entry in `CHANGELOG.md`:
   ```bash
   git diff main...HEAD -- CHANGELOG.md
   ```
2. If the PR changes observable behavior and lacks a changelog update, identify the change category (`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`).

### 2. Formulate Entry
1. Follow `changelog` formatting:
   - One line per logical change with active verb in past tense or imperative.
   - Reference PR number and author where appropriate.
   - Place entry under the `## [Unreleased]` section.

### 3. Commit & Verify
1. Commit the changelog entry on the PR branch:
   ```bash
   git commit -m "docs(changelog): add entry for PR #<n>" CHANGELOG.md
   ```
2. Verify that linting and checks pass.
