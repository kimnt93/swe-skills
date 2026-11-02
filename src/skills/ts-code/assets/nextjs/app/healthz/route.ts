import { hostname } from "node:os";
import { buildHealthz } from "@/lib/healthz";

export const dynamic = "force-dynamic";

const startedAt = new Date();

export function GET() {
  const body = buildHealthz(
    {
      serviceName: process.env.SERVICE_NAME ?? "web",
      envName: process.env.ENV_NAME ?? "local",
      nodeName: process.env.NODE_NAME ?? hostname(),
      serviceVersion: process.env.SERVICE_VERSION ?? "0.0.0",
      startedAt,
    },
    new Date(),
  );
  return Response.json(body, { headers: { "cache-control": "no-store" } });
}
