import { ApiError, createClient } from "./client";

function respond(body: unknown, status = 200) {
  return async () => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

test("unwraps data from a successful envelope", async () => {
  const client = createClient("http://api", respond({
    success: true, status_code: 200, message: "ok", data: { id: "o1" }, error: { code: "", retryable: false },
  }));
  await expect(client.get<{ id: string }>("/v1/orders/o1")).resolves.toEqual({ id: "o1" });
});

test("throws ApiError with the envelope's error code", async () => {
  const client = createClient("http://api", respond({
    success: false, status_code: 422, message: "over the risk limit", data: null,
    error: { code: "risk_limit", retryable: false },
  }, 422));
  await expect(client.post("/v1/orders", {})).rejects.toMatchObject({ name: "ApiError", code: "risk_limit", status: 422 });
});

test("a non-JSON response is an ApiError, not a crash", async () => {
  const client = createClient("http://api", async () => new Response("<html>bad gateway</html>", { status: 502 }));
  const error = await client.get("/v1/orders").catch((e: unknown) => e);
  expect(error).toBeInstanceOf(ApiError);
  expect((error as ApiError).code).toBe("invalid_response");
});
