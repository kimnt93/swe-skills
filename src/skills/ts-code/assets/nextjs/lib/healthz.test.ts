import { expect, test } from "vitest";
import { buildHealthz } from "./healthz";

const REQUIRED = [
  "status", "service_name", "env_name", "node_name", "api_versions", "service_version",
  "started_at", "checked_at", "uptime_seconds", "config", "checks",
];

test("has every field the api-contract healthz schema requires", () => {
  const body = buildHealthz(
    { serviceName: "web", envName: "local", nodeName: "n1", serviceVersion: "1.0.0", startedAt: new Date("2026-01-01T00:00:00Z") },
    new Date("2026-01-01T00:01:30Z"),
  );
  expect(Object.keys(body).sort()).toEqual([...REQUIRED].sort());
  expect(body.uptime_seconds).toBe(90);
  expect(body.status).toBe("ok");
});
