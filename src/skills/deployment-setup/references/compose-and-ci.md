# Compose layouts and CI

Discover file paths, workflow providers, supported environments and caller inputs from the target
project. Preserve existing conventions; do not copy another project's concrete deployment values.
For writing the files themselves see [Swarm Compose](swarm-compose.md), [Dockerfile](dockerfile.md),
[Traefik labels](traefik-labels.md) and [CI workflows](ci-workflows.md); this page covers layout choices.

| Layout | Guidance |
|---|---|
| One file with several services | Treat it as one application model; determine shared lifecycle and dependencies |
| Base plus override files | Preserve merge order and path resolution; inspect the final service set |
| Independent files | Assign unique stacks/projects and record ownership per target |
| Several services sharing an image | Separate runtime configuration from the image build |
| Multiple images | Map each build component to the corresponding runtime image input |

A reusable workflow may accept one file rather than a list. Inspect its interface before choosing
multiple callers, a matrix or a combined contract. Build inputs do not necessarily select runtime
services. Avoid deploying independently pruned partial models to the same stack: omitted services
can be removed by the other deployment.

CI should bind deployment to the intended revision and immutable image, serialize changes to each
target and preserve required test/scan evidence. Check how the project handles environment triggers,
registry access, secrets preflight and migrations. Build networking and runtime networking are
separate choices. A separately triggered green workflow does not automatically gate deployment.

For merged files, validate the actual result with the intended runtime; Compose features may not
be supported by Swarm. Avoid repeated interpolation of already rendered output. For independent
stacks, ordering requires explicit readiness or completion gates rather than cross-stack
`depends_on` assumptions.

Verification covers the whole affected model and every deployment target. A successful apply or
replica count does not prove protocol behavior. Recovery must account for configuration, images,
schema, storage and external changes; service rollback alone may not reverse all of them.

## Example usage

- “Set up deployment for a base Compose file and its environment overrides.”
- “Add independent CI deployment targets for these Compose files.”
- “Review whether this workflow deploys the image that CI actually tested.”
