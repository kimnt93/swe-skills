# Host and service mapping

Discover topology from the target project's inventory and focused infrastructure inspection.
Do not embed a fixed host map in the skill or infer physical placement from runner names.

Distinguish the CI execution host, Docker control endpoint, runtime node and client ingress
address. Check eligible nodes, role/workload labels, capacity, storage ownership and connectivity.
A worker role may match several hosts, and a deployment environment label is not live evidence.

Record these fields in the target project's deployment notes:

| Area | Information to discover |
|---|---|
| Identity | Service, environment, stack/project and deployment owner |
| Placement | Constraints, eligible nodes, observed runtime host and observation time |
| Image | Build input, runtime image variable and observed digest |
| Networking | Networks, aliases, dependencies, ingress and port ownership |
| State | Volume/bind/object-storage owner, persistence namespace and recovery boundary |
| Secrets | Logical name, external generation, mount and consumer |

Use existing authorized access and focused read-only queries. Inspect metadata without printing
credential values. Confirm network aliases resolve in the intended scope, ingress reaches the
protocol and storage is available on the selected host. Moving a task does not automatically move
host-local data. Host networking does not establish host identity inside the container.

Separate desired configuration from observed state. Record target, timestamp and evidence
boundary. Missing access means live state is unverified. Infrastructure provisioning remains
separate from discovering the host map.

## Example usage

- “Map these Compose services to eligible hosts and identify placement gaps.”
- “Review network access and storage ownership before deploying this stack.”
