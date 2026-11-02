# Multiple services in one repository

One repository can deploy several related services. They may share a Dockerfile and image while
using different runtime configuration, or have independent build components. Keep the concrete
service list and configuration in the target repository.

Choose a combined stack when the services share one deployment lifecycle. Choose separate
stacks/projects when independent rollout and ownership are required. Preserve an established
layout rather than forcing a repository split.

A matrix can deploy independent targets. Derive a unique target and file for each entry from
project configuration; do not send several partial models to the same pruned stack. Choose
parallelism for available capacity and avoid cancelling sibling rollouts mid-update. Record
partial success because a multi-target deployment is not necessarily atomic.

Clarify whether each entry builds independently or all entries consume one tested image. For a
shared-image handoff, verify the reusable workflow supports the selected environment and binds
the image receipt to the source revision. Do not assume repeated builds produce identical digests.

Run finite migrations through a completion gate before dependent services. A migration process
that exits successfully is not a continuously running service. Avoid placing migrations in a
parallel service matrix or executing the same migration from every entry.

Scope secret mounts to each consumer and discover how the secret project is derived. Separate
consumer groups, state namespaces and service identity where needed. Several services does not
imply that each stateful service supports multiple replicas or overlapping updates.

Verify each file, image input, target name, secret reference and placement requirement. Check
that documented workflows actually exist. Exercise the whole dependency flow after an authorized
rollout. Replacing a combined stack requires a cutover plan for duplicate consumers, state writers,
recovery resources and rollback ordering.

## Example usage

- “Deploy each service in this repository as an independent stack using a CI matrix.”
- “Build one tested image and reuse it across these deployment targets.”
- “Add a migration completion gate before the services that depend on its schema.”
