# Change log format

Repo `CHANGELOG.md` follows Keep a Changelog, newest first:

```markdown
# Changelog

## [Unreleased]

### Added
- Cancel an open order with `DELETE /v1/orders/{id}` ([#41](https://github.com/acme/api/pull/41))

### Fixed
- Fills are no longer counted twice when Kafka redelivers ([#44](https://github.com/acme/api/pull/44))

## [1.3.0] - 2026-10-30

### Changed
- **Breaking:** `GET /v1/positions` returns `qty` as a string. Parse it as a decimal. ([#38](https://github.com/acme/api/pull/38))
```

- Headings: `Added`, `Changed`, `Fixed`, `Removed`, `Security`, `Deprecated`. Omit empty ones.
- Dates are `YYYY-MM-DD`, UTC. Versions follow semantic versioning.
- Links to PRs are full URLs so the log reads anywhere.

Project log `changelog/project.md` (written by the CLI and the manager):

```markdown
# Project change log

## 2026-11

- 2026-11-04 `api` feat: cancel an open order ([#41](https://github.com/acme/api/pull/41))
- Order cancellation: API ([api#41](https://github.com/acme/api/pull/41)), dashboard ([web#17](https://github.com/acme/web/pull/17))
```

`changelog/<repo>.md` has the same month layout with only that repo's merged PRs.
