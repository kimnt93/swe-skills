// node smoke.ts   (Node 22.18+ / 24+ runs TypeScript directly; no build step)
import assert from "node:assert/strict";
import { bareToken, buildHealthz, buildInternal, callerFromHeaders, identityFromEnv, isInternalToken } from "./healthz.ts";

const id = identityFromEnv({ SERVICE_NAME: "account-api", ENV_NAME: "stg", NODE_NAME: "node-1", PORT: "3000" });
const down = {
  name: "postgres",
  ping: async () => {
    throw new Error("dial postgres://u:secret@pg refused");
  },
};
const up = { name: "redis", ping: async () => {} };

const healthy = await buildHealthz(id, [up]);
assert.equal(healthy.statusCode, 200);
assert.equal(healthy.body.status, "ok");
assert.equal(healthy.body.service_name, "account-api");
assert.equal(healthy.body.env_name, "stg");
assert.equal(healthy.body.node_name, "node-1");
assert.deepEqual(healthy.body.api_versions, ["v1"]);
assert.equal(healthy.body.config.port, 3000);
assert.equal(healthy.body.config.docs_url, "/docs");

const empty = await buildHealthz(id, []);
assert.deepEqual(empty.body.checks, []);

const broken = await buildHealthz(id, [down, up]);
assert.equal(broken.statusCode, 503);
assert.equal(broken.body.status, "down");
assert.equal(broken.body.checks[0]?.error, "unavailable");
assert.equal(broken.body.checks[1]?.status, "ok");
assert.ok(!JSON.stringify(broken.body).includes("secret"), "the error text must not leak");

const fromRun = identityFromEnv({ SERVICE_NAME: "x", RUN_ENV: "prod" });
assert.equal(fromRun.envName, "prod");
assert.throws(() => identityFromEnv({}), /SERVICE_NAME is required/);
assert.equal(bareToken("Bearer tok"), "tok");
assert.equal(bareToken("  bearer   tok "), "tok");
assert.equal(bareToken("tok"), "tok");
for (const value of ["tok", "Bearer tok", "bearer tok"]) assert.ok(isInternalToken(value, "tok"), value);
assert.ok(!isInternalToken(undefined, "tok") && !isInternalToken("nope", "tok") && !isInternalToken("tok", ""));
const caller = callerFromHeaders({ "x-user-id": " u-7 ", "x-username": "linh" });
assert.deepEqual(caller, { user_id: "u-7", username: "linh" });
assert.deepEqual(callerFromHeaders({}), { user_id: "", username: "" });
const internal = await buildInternal(id, [], caller);
assert.equal(internal.statusCode, 200);
assert.deepEqual(internal.body.caller, caller);
assert.equal(internal.body.service_name, "account-api");
console.log("healthz smoke ok");
