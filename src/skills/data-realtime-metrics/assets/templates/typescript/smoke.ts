/**
 * Smoke test: emit every metric once so scripts/otlp_check.py can verify the contract.
 *
 *   python3 scripts/otlp_check.py --role ingestion --wait 20 &
 *   npx tsx smoke.ts http://127.0.0.1:4318 ingestion
 */
import { PipelineMetrics } from './pipelineMetrics.js';

const [endpoint, role] = process.argv.slice(2);
const m = new PipelineMetrics({
  service: `ssi-ws-v3-${role === 'ingestion' ? 'feed' : role}`,
  environment: 'local',
  endpoint,
  exportIntervalMs: 1000,
  ingestion: role === 'ingestion',
});
m.setKafkaHealthy(true);
m.setBacklog(() => 3);
if (role === 'ingestion') {
  m.setConnected(true);
  m.setInFlight(() => 2);
  m.reconnect();
}
m.received({ count: 2 });
m.received({ live: false });
m.dropped();
m.published({ count: 2, bytes: 128, latencyMs: 4.2 });
m.error();
setTimeout(() => m.shutdown().catch((e: Error) => console.error('final flush:', e.message)), 3000);
