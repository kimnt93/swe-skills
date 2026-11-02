import { expect, test } from "@playwright/test";

test("/healthz answers the api-contract body", async ({ request }) => {
  const response = await request.get("/healthz");
  expect(response.status()).toBe(200);
  expect(response.headers()["cache-control"]).toContain("no-store");
  const body = await response.json();
  expect(body).toMatchObject({ status: "ok", service_name: "web", env_name: "local" });
});

test("the orders page degrades when the API is down", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Orders" })).toBeVisible();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("unreachable");
});
