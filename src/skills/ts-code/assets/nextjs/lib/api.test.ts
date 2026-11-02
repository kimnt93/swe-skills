import { describe, expect, test } from "vitest";
import { ApiError, createClient } from "./api";

const ok = (data: unknown) =>
  async () => new Response(JSON.stringify({ success: true, status_code: 200, message: "ok", data, error: { code: "", retryable: false } }));

describe("createClient", () => {
  test("unwraps data", async () => {
    await expect(createClient("http://api", ok([1, 2])).get("/v1/x")).resolves.toEqual([1, 2]);
  });

  test("an error envelope becomes ApiError with its code", async () => {
    const client = createClient("http://api", async () => new Response(JSON.stringify({
      success: false, status_code: 404, message: "no such order", data: null, error: { code: "not_found", retryable: false },
    }), { status: 404 }));
    await expect(client.get("/v1/orders/x")).rejects.toMatchObject({ code: "not_found", status: 404 });
  });

  test("an unreachable API is a retryable ApiError", async () => {
    const client = createClient("http://api", async () => { throw new TypeError("fetch failed"); });
    const error = await client.get("/v1/x").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "unreachable", retryable: true });
  });
});
