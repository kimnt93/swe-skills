# Secrets management

Discover the project's approved secret manager, ownership model, naming convention and runtime
delivery mechanism. For an existing platform workflow, reuse its supported preflight rather
than adding parallel provisioning. Distinguish runtime, build, registry and CI-only credentials.

Commit references and non-secret placeholders only. A password, key or token has no default value in
Compose (`${X_PASSWORD:?message}` or a mounted `*_FILE` secret), and `.env.example` leaves it blank. Attach secrets only to consumers that need
them. Verify application file-secret support or the existing wrapper; a variable ending in
`_FILE` does not itself implement file reading. Check runtime-user readability and fail-closed
behavior without displaying values.

Swarm external secrets and standalone Compose file-backed secrets have different delivery and
permission behavior. Select the supported mechanism for the target runtime and verify actual
permissions. Do not assume Swarm secret names work in standalone Compose.

For immutable secret stores, rotate through a new generation rather than changing an existing
one. Preserve stable mount paths when supported, coordinate providers and consumers, and retain
rollback compatibility until retirement is authorized. Rotation does not universally guarantee
zero downtime.

Build credentials belong in supported secret mounts, not build arguments or image layers.
Registry credentials need the correct lifetime and scope for build publication and later runtime
pulls. Isolate job credential configuration where shared runners could race. Keep CI-only
credentials separate from application mounts.

Validate references, missing-secret failure, rotation and leakage with dummy values. Avoid full
environment/auth dumps, secret responses and shell tracing around credential delivery.

## Example usage

- “Add runtime secret mounts for the credentials this application consumes.”
- “Review secret provisioning and rotation for these deployment targets.”
- “Separate build, registry and application credentials in this workflow.”
