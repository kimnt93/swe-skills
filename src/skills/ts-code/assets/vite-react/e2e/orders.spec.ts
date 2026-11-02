import { expect, test } from "@playwright/test";

test("the orders page renders the API's orders", async ({ page }) => {
  await page.route("**/v1/orders", (route) =>
    route.fulfill({
      json: {
        success: true, status_code: 200, message: "ok",
        data: [{ id: "o1", symbol: "VN30F", side: "buy", qty: 1, price: "1250.5", status: "open" }],
        error: { code: "", retryable: false },
      },
    }),
  );
  await page.goto("/");
  await expect(page.getByRole("table", { name: "Orders" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "VN30F" })).toBeVisible();
});
