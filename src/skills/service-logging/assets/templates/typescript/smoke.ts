/**
 * Smoke test: emit the line types a service produces, then validate them:
 *
 *   SERVICE_NAME=ssi-ws-v3 ENV_NAME=local NODE_NAME=docker-host-1 LOG_LEVEL=debug npx tsx smoke.ts \
 *     | python3 ../../../scripts/logcheck.py --service ssi-ws-v3 --env local --node docker-host-1 --require-trace
 */
import { trace } from '@opentelemetry/api';
import { NodeTracerProvider } from '@opentelemetry/sdk-trace-node';
import { configureFromEnv, getLogger } from './serviceLogging.js';

configureFromEnv();
const log = getLogger();
log.info({ messages_received: 361234, messages_published: 361233, channel_depth: 0 }, 'message statistics');
getLogger('api.request').warn({ request_id: 'r-1', duration_ms: 1250.5 }, 'slow request');
log.debug({ ok: true }, 'debug line');
log.error({ error: new Error('sink write failed'), table: 'trades' }, 'write failed');

new NodeTracerProvider().register();
trace.getTracer('smoke').startActiveSpan('work', (span) => {
  log.info('inside a span');
  span.end();
});
