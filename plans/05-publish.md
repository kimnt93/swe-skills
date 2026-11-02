# 05 — publish

status: done (tool) · human: choosing and creating the publish remote

## Goal

Teammates install the plugin without this source repo.

## What exists

`scripts/publish.sh` (`make publish`, `PUSH=1` to push): builds, validates, requires a
`CHANGELOG.md` entry for the version, syncs `dist/<name>/` into a publish repo
(`PUBLISH_DIR`, default `~/src/<name>-plugin`), commits `release: <name> <version>` and tags
`v<version>`. It refuses a dirty publish repo and a changed release under an existing tag.

## Human steps

1. Decide visibility: the domain skills describe internal conventions, so a private repo is the
   safe default.
2. Create the remote (for example `gh repo create <owner>/<name>-plugin --private`) and add it:
   `git -C ~/src/<name>-plugin remote add origin <url>`.
3. Bump `PLUGIN_VERSION` in `plugin.env`, add the `CHANGELOG.md` entry, then `make publish PUSH=1`.
4. Teammates: `claude plugin marketplace add <owner>/<name>-plugin` and
   `claude plugin install <name>@<name>-skills`.

## Verify

```bash
PUBLISH_DIR=$(mktemp -d) bash scripts/publish.sh    # release + tag; a second run says "no change"
```

## Log

- 2026-11-02: publish script tested: first release, no-op re-run, refused re-tag with changed content.
