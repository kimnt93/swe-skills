// GET /healthz body for the frontend, in the api-contract shape (root path, not under /v1).
// `config` is an allowlist of non-secret values: never spread process.env into it.

export interface Healthz {
  status: "ok" | "down";
  service_name: string;
  env_name: string;
  node_name: string;
  api_versions: string[];
  service_version: string;
  started_at: string;
  checked_at: string;
  uptime_seconds: number;
  config: Record<string, string | number | boolean>;
  checks: { name: string; status: "ok" | "down"; latency_ms: number; error: string }[];
}

export interface Identity {
  serviceName: string;
  envName: string;
  nodeName: string;
  serviceVersion: string;
  startedAt: Date;
}

export function buildHealthz(identity: Identity, now: Date): Healthz {
  return {
    status: "ok",
    service_name: identity.serviceName,
    env_name: identity.envName,
    node_name: identity.nodeName,
    api_versions: [],
    service_version: identity.serviceVersion,
    started_at: identity.startedAt.toISOString(),
    checked_at: now.toISOString(),
    uptime_seconds: Math.max(0, Math.floor((now.getTime() - identity.startedAt.getTime()) / 1000)),
    config: { port: 3000 },
    checks: [],
  };
}
