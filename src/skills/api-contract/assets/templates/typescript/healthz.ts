// GET /healthz for a TypeScript/JavaScript service (api-contract skill): the one health endpoint,
// at the root next to /docs and not under /v1. Framework neutral: `buildHealthz` returns the HTTP
// status and the JSON body, which lists every API version in `api_versions`.
//
//   Fastify  app.get("/healthz", async (_req, reply) => {
//              const { statusCode, body } = await buildHealthz(identity, checks);
//              return reply.code(statusCode).header("Cache-Control", "no-store").send(body);
//            });
//   Express  app.get("/healthz", async (_req, res) => {
//              const { statusCode, body } = await buildHealthz(identity, checks);
//              res.status(statusCode).set("Cache-Control", "no-store").json(body);
//            });
//
// /internal is the same body behind the service token plus the caller (see "Internal calls" in
// the skill): check `isInternalToken(req.headers["x-internal-service-token"], token)` first, answer
// 401 in the envelope when false, then `buildInternal(identity, checks, callerFromHeaders(req.headers))`.
//
// Register /healthz BEFORE the auth middleware: health is public. `config` is an allowlist of
// non-secret values: add a key on purpose, never spread process.env into it.

import { timingSafeEqual } from "node:crypto";
import { hostname } from "node:os";

export interface Identity {
  serviceName: string;
  envName: string;
  nodeName: string;
  serviceVersion: string;
  startedAt: Date;
  config: Record<string, string | number | boolean | string[]>;
}

/** A dependency the service cannot work without. Throw (or reject) when it is down. */
export interface Check {
  name: string;
  ping: () => Promise<void>;
}

export interface CheckResult {
  name: string;
  status: "ok" | "down";
  latency_ms: number;
  error: "" | "timeout" | "unavailable";
}

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
  config: Record<string, string | number | boolean | string[]>;
  checks: CheckResult[];
}

/** The versions this service serves (/v1, /v2), listed by /healthz. */
/** Who the calling service says it acts for (x-user-id, x-username); "" when absent. */
export interface Caller {
  user_id: string;
  username: string;
}

export interface InternalHealthz extends Healthz {
  caller: Caller;
}

export const API_VERSIONS = ["v1"];
export const DEFAULT_PORT = 3000;
const CHECK_TIMEOUT_MS = 2000;

/** The identity from the environment: the same names and order as the log format. */
export function identityFromEnv(env: NodeJS.ProcessEnv = process.env): Identity {
  const port = Number(env.PORT ?? DEFAULT_PORT);
  return {
    serviceName: required(env, "SERVICE_NAME"),
    envName: env.DEVELOPMENT_ENVIRONMENT || env.ENV_NAME || env.RUN_ENV || "local",
    nodeName: env.NODE_NAME || hostname(),
    serviceVersion: env.SERVICE_VERSION ?? "",
    startedAt: new Date(),
    config: {
      port,
      log_level: env.LOG_LEVEL ?? "info",
      docs_url: "/docs",
    },
  };
}

export async function buildHealthz(
  id: Identity,
  checks: Check[],
  now: Date = new Date(),
): Promise<{ statusCode: 200 | 503; body: Healthz }> {
  const results = await Promise.all(checks.map(runCheck));
  const down = results.some((result) => result.status !== "ok");
  const body: Healthz = {
    status: down ? "down" : "ok",
    service_name: id.serviceName,
    env_name: id.envName,
    node_name: id.nodeName,
    api_versions: API_VERSIONS,
    service_version: id.serviceVersion,
    started_at: id.startedAt.toISOString(),
    checked_at: now.toISOString(),
    uptime_seconds: Math.max(0, Math.floor((now.getTime() - id.startedAt.getTime()) / 1000)),
    config: id.config,
    checks: results,
  };
  return { statusCode: down ? 503 : 200, body };
}

async function runCheck(check: Check): Promise<CheckResult> {
  const start = performance.now();
  let error: CheckResult["error"] = "";
  let timer: NodeJS.Timeout | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error("timeout")), CHECK_TIMEOUT_MS);
  });
  try {
    await Promise.race([check.ping(), timeout]);
  } catch (cause) {
    // The response carries a short code, never the message (it can hold a host or a DSN).
    error = cause instanceof Error && cause.message === "timeout" ? "timeout" : "unavailable";
    console.warn(JSON.stringify({ level: "warn", msg: "health check failed", check: check.name, error: String(cause) }));
  } finally {
    clearTimeout(timer);
  }
  return {
    name: check.name,
    status: error === "" ? "ok" : "down",
    latency_ms: Math.round((performance.now() - start) * 10) / 10,
    error,
  };
}

function required(env: NodeJS.ProcessEnv, name: string): string {
  const value = env[name]?.trim();
  if (!value) throw new Error(`${name} is required`);
  return value;
}

/** The token without an optional case-insensitive `Bearer ` prefix: both header forms are valid. */
export function bareToken(value: string | undefined): string {
  const trimmed = (value ?? "").trim();
  return /^bearer\s/i.test(trimmed) ? trimmed.slice(7).trim() : trimmed;
}

/** Constant-time check of `x-internal-service-token`; false when either side is empty. */
export function isInternalToken(header: string | string[] | undefined, expected: string): boolean {
  const got = Buffer.from(bareToken(Array.isArray(header) ? header[0] : header));
  const want = Buffer.from(expected);
  return want.length > 0 && got.length === want.length && timingSafeEqual(got, want);
}

/** `x-user-id` / `x-username`, trimmed and capped at 128 characters. Trust only after the token check. */
export function callerFromHeaders(headers: Record<string, string | string[] | undefined>): Caller {
  const read = (name: string): string => {
    const value = headers[name];
    return (Array.isArray(value) ? value[0] : value)?.trim().slice(0, 128) ?? "";
  };
  return { user_id: read("x-user-id"), username: read("x-username") };
}

/** The /internal body: the /healthz body plus the caller. */
export async function buildInternal(
  id: Identity,
  checks: Check[],
  caller: Caller,
  now: Date = new Date(),
): Promise<{ statusCode: 200 | 503; body: InternalHealthz }> {
  const { statusCode, body } = await buildHealthz(id, checks, now);
  return { statusCode, body: { ...body, caller } };
}
