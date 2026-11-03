/**
 * Unified service logging on pino (see references/log-format.md). Copy this file into the
 * service; call configureFromEnv() once at startup, then log anywhere:
 *
 *   import { configureFromEnv, getLogger, errorFields } from './serviceLogging.js';
 *
 *   configureFromEnv();                      // SERVICE_NAME, DEVELOPMENT_ENVIRONMENT|ENV_NAME, NODE_NAME, LOG_LEVEL
 *   const log = getLogger();                 // logger = "root"
 *   const api = getLogger('api.request');    // named logger
 *   log.info({ messages_received: 361234, channel_depth: 0 }, 'message statistics');
 *   log.error({ error: err, table: 'trades' }, 'sink write failed');   // error, error_type, stack
 *
 * Every line has level, development_environment, service_name, node_name, logger, time (UTC
 * RFC 3339, 9 fractional digits), caller (<root>/<relative path>:<line>) and message, plus
 * trace_id/span_id inside an active OpenTelemetry span. Custom fields stay flat and snake_case.
 * Computing `caller` captures a stack per line: log per operation, never per message in a hot
 * path (set LOG_CALLER=false to drop the field only where that is acceptable).
 */
import { existsSync } from 'node:fs';
import { hostname } from 'node:os';
import { basename, dirname, join, relative } from 'node:path';
import { isSpanContextValid, trace } from '@opentelemetry/api';
import pino, { type DestinationStream, type Logger } from 'pino';

export type { Logger };

export interface LoggingOptions {
  service: string;
  environment: string;
  /** Defaults to the hostname (a container id in a bridge-network container). */
  node?: string;
  level?: string;
  destination?: DestinationStream;
  /** Directory the caller path is relative to; default: nearest ancestor with package.json. */
  root?: string;
}

const THIS_FILE = import.meta.url.replace(/^file:\/\//, '');
let base: Logger | undefined;
let rootDir = process.cwd();
let withCaller = true;

/** SERVICE_NAME (required); DEVELOPMENT_ENVIRONMENT else ENV_NAME else "local"; NODE_NAME (in
 * Docker set it to the host name); LOG_LEVEL (default info). */
export function configureFromEnv(overrides: Partial<LoggingOptions> = {}): void {
  const service = process.env.SERVICE_NAME;
  if (!service) throw new Error('SERVICE_NAME is required (the pipeline/service name, e.g. feed-ws)');
  configure({
    service,
    environment: process.env.DEVELOPMENT_ENVIRONMENT || process.env.ENV_NAME || 'local',
    node: process.env.NODE_NAME || undefined,
    level: process.env.LOG_LEVEL,
    ...overrides,
  });
  withCaller = process.env.LOG_CALLER !== 'false';
}

export function configure(o: LoggingOptions): void {
  rootDir = o.root ?? findRoot();
  base = pino(
    {
      level: normalizeLevel(o.level ?? 'info'),
      messageKey: 'message',
      errorKey: 'error',
      base: { development_environment: o.environment, service_name: o.service, node_name: o.node ?? hostname() },
      timestamp: () => `,"time":"${nowIso()}"`,
      formatters: { level: (label) => ({ level: label }) },
      serializers: { error: (e: unknown) => (e instanceof Error ? e.message : e) },
      mixin: (merged: object, level: number) => {
        const error = (merged as { error?: unknown }).error;
        return {
          ...(withCaller ? { caller: callerOf() } : {}),
          ...traceIds(),
          ...(error instanceof Error ? errorFields(error, level >= 50) : {}),
        };
      },
    },
    o.destination ?? pino.destination(1),
  );
}

/** A named logger: logger=name (the root logger is "root"). */
export function getLogger(name = 'root'): Logger {
  if (!base) throw new Error('call configure() or configureFromEnv() first');
  return base.child({ logger: name });
}

/** error_type and stack for an Error (the `error` message itself comes from the serializer). */
export function errorFields(error: Error, withStack = true): Record<string, string> {
  return { error_type: error.name, ...(withStack && error.stack ? { stack: error.stack.slice(0, 8000) } : {}) };
}

function normalizeLevel(level: string): string {
  const l = level.toLowerCase();
  return l === 'warning' ? 'warn' : l === 'critical' ? 'fatal' : l;
}

// -- time: nanosecond digits from the monotonic clock, anchored to the wall clock -------------

let originNs = BigInt(Date.now()) * 1_000_000n - process.hrtime.bigint();
function nowIso(): string {
  let ns = originNs + process.hrtime.bigint();
  const wallMs = Date.now();
  if (Math.abs(Number(ns / 1_000_000n) - wallMs) > 1000) {
    // The wall clock was stepped (NTP, suspend): re-anchor.
    originNs = BigInt(wallMs) * 1_000_000n - process.hrtime.bigint();
    ns = originNs + process.hrtime.bigint();
  }
  const ms = Number(ns / 1_000_000n);
  const frac = String(ns % 1_000_000_000n).padStart(9, '0');
  return new Date(ms).toISOString().slice(0, 19) + `.${frac}Z`;
}

// -- trace ids ------------------------------------------------------------------------------

function traceIds(): Record<string, string> {
  const context = trace.getActiveSpan()?.spanContext();
  return context && isSpanContextValid(context) ? { trace_id: context.traceId, span_id: context.spanId } : {};
}

// -- caller: <root>/<relative path>:<line> of the first frame outside this file and pino -------

function findRoot(): string {
  let dir = process.cwd();
  while (dir !== dirname(dir)) {
    if (existsSync(join(dir, 'package.json'))) return dir;
    dir = dirname(dir);
  }
  return process.cwd();
}

const FRAME = /\(?((?:file:\/\/)?\/[^()\s]+?):(\d+):\d+\)?$/;
function callerOf(): string {
  const saved = Error.stackTraceLimit;
  Error.stackTraceLimit = 25;
  const stack = new Error().stack ?? '';
  Error.stackTraceLimit = saved;
  for (const line of stack.split('\n').slice(1)) {
    const match = FRAME.exec(line.trim());
    if (!match) continue;
    const file = match[1].replace(/^file:\/\//, '');
    if (file === THIS_FILE || file.includes('/node_modules/pino/') || file.includes('/node_modules/thread-stream/')) continue;
    const nm = file.indexOf('/node_modules/');
    const shown = nm >= 0 ? file.slice(nm + 1) : file.startsWith(rootDir + '/') ? `${basename(rootDir)}/${relative(rootDir, file)}` : basename(file);
    return `${shown}:${match[2]}`;
  }
  return 'unknown:1';
}
