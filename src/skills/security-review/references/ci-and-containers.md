# CI and containers

## What to look for

- **CI:** a trigger that runs an outsider's code with secrets (`pull_request_target` or `workflow_run` with a checkout
  of the pull request); wider `permissions`; a secret passed to a new step or third-party action; outsider text
  (title, branch, comment) expanded inside `run`; actions not pinned by commit; a self-hosted runner for outside pull
  requests; artifacts or caches that hold secrets or that an outsider can fill; **a removed or weakened check**.
- **Containers:** runs as root; privileged, the Docker socket, host network or wide mounts; secrets in `ARG`, `ENV` or
  a layer; no `.dockerignore` for `.env` and keys; ports published that need not be.

Every step that calls out or uploads is also [outbound data](outbound-data.md).

## Bad

```yaml
on: pull_request_target
permissions: write-all
steps:
  - run: echo "Title: ${{ github.event.pull_request.title }}" # the title runs as shell code
```

## Good

```yaml
on: pull_request
permissions:
  contents: read
steps:
  - env:
      TITLE: ${{ github.event.pull_request.title }}
    run: printf 'Title: %s\n' "$TITLE"
```

## Prove it

Quote the trigger, the permissions and the line that uses the value; run the `run` script locally with a made-up title
such as `"; touch proof #` and check that no file appears. For an image: build it locally and print its user
(`docker image inspect --format '{{.Config.User}}' <image>`). Never try an attack through the real repository's CI.
