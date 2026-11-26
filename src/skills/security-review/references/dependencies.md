# Dependencies and supply chain

## What to look for

For each new or moved package, image, action or tool: does the issue need it; is the name the real one (not a
look-alike); is it maintained; is it locked, from the usual registry; what does it run on install, build or import;
does it send anything ([outbound data](outbound-data.md)); which packages come with it. Also: a lock file changed
with no manifest change, a source replaced (`replace`, `[patch]`, an extra index), an action or image not pinned by
commit or digest, a download piped into a shell, vendored or minified code nobody can read.

## Bad

```dockerfile
FROM python:latest
RUN curl -fsSL https://tools.example.com/install.sh | sh
```

## Good

```dockerfile
FROM python:3.13-slim@sha256:<digest>
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
```

## Prove it

Show the lock file's new entries and read each new package's source **at the locked version** (fetched without running
install scripts): its install hooks and the calls it makes. Run the project's own vulnerability check
(`govulncheck`, `pip-audit`, `cargo audit`, `npm audit`) and report what the pull request adds. These send the
dependency list to a database: on a private project use one only where the project already does. A known flaw that
this code can reach blocks.
