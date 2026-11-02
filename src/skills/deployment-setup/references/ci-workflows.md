# CI workflows

Write thin caller workflows that delegate build and deploy to the project's reusable workflow, plus
a validation workflow. **Read the reusable workflow first** (its `workflow_call` inputs, permissions,
triggers it accepts) and copy the closest existing caller; the input names below are the common
shape, not a guarantee. Starting points: `assets/templates/workflows/`.

## Triggers and environments

| Plane | Trigger | Notes |
|---|---|---|
| staging (`stg`) / common | `push` to `main` + `workflow_dispatch` | Deploys the revision that was just built. |
| production (`prod`) | `release: types: [published]` | Guard the job: `startsWith(github.event.release.tag_name, 'v') && !github.event.release.draft && !github.event.release.prerelease`. |
| release creation | tag push `v*.*.*` creates a release | Events created by the default `GITHUB_TOKEN` do not start other workflows; check how the project creates releases so the production workflow actually fires. |

A reusable workflow normally serialises per repository/plane/stack. Do not add your own
`concurrency` that cancels an active stateful rollout.

## Caller shape

```yaml
permissions:
  contents: read            # workflow default: least privilege

jobs:
  deploy:
    permissions:            # permissions are granted on the job
      contents: read
      id-token: write       # needed by secret preflight; grant even if no secrets
      packages: write       # only if the reusable workflow publishes to GHCR
    uses: <org>/<workflows-repo>/.github/workflows/swarm-deploy.yml@main
    with:
      environment: stg
      stack: example
```

A called workflow cannot request more permission than its caller job grants; missing grants fail the
whole run at startup. Do not grant workflow-level write permissions.

## Common inputs

| Input | Use |
|---|---|
| `environment` | Plane name accepted by the workflow (for example `stg`, `prod`). |
| `stack` | Stack name **without** the plane suffix; the deployed stack is `<stack>-<plane>`. |
| `compose_file` | Swarm file to deploy (default usually `docker-compose.yaml`). One caller per independent file. |
| `services` / `dockerfiles` | Build contexts and aligned Dockerfiles. `root` = repo root and `Dockerfile`; `root:<component>` = one context, several components. Each derives an image variable (`<COMPONENT>_IMAGE`, upper-case with `_`), which the Compose file must consume. |
| `image_names` | A complete tested `VARIABLE=<image>@sha256:<digest>` map that skips building (shared-image handoff); verify it is bound to the source revision. |
| `build_args` | Non-secret `KEY=VALUE` lines only. |
| `build_network` | `default`, `host` or `none` for Dockerfile `RUN` steps; builder networking is separate. |
| `migration_compose_file` | Optional migration job completed before the application apply. |
| `node_role` | Value for the `node.role` placement constraint. |

Derive the image variable for each component and confirm the Compose file references exactly those
names; an unmapped variable fails rendering and an extra image is never deployed.

## Validation workflow

Run on pull requests (same-repository only) and dispatch, on the project's trusted runner labels:

- check out with `persist-credentials: false`;
- render each plane: load `deploy/<plane>.env`, set dummy `RUN_ENV`/image variables, run
  `docker stack config` (and `docker compose -f docker-compose.local.yaml config`);
- lint workflows (`actionlint`) and declare self-hosted runner labels in `.github/actionlint.yaml`;
- run the project's tests/vet/vulnerability checks in the same toolchain image the Dockerfile builds with;
- optional weekly scheduled scan.

Fork-originated PRs must not run on self-hosted runners:
`github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository`.

## Hardening

- Pin third-party actions to a full commit SHA with the version as a comment; keep `dependabot.yml` for
  `github-actions` so pins move.
- No secrets in workflow files, build args or `echo`; no `set -x` around credential steps.
- Do not rely on a separately triggered green workflow as a deploy gate; make deploy depend on the
  tests (`needs:`) or on image-receipt verification.
- Keep the shared workflow reference stable and review changes to it: `@main` makes the reusable
  workflow a live dependency of every caller.

## Several targets

For independent files/stacks, use one caller job per target or a matrix over `{stack, compose_file,
image variable}` derived from project config; never send several partial models to the same stack.
Set `fail-fast: false`, bound parallelism to host capacity and record partial success. Add migration
completion gates rather than cross-stack `depends_on` ([multi-service](multi-service-pipelines.md)).

## Example usage

- “Add staging and production caller workflows for this service.”
- “Add PR validation that renders both planes with dummy variables.”
