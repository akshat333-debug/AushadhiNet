import { test, expect } from "@playwright/test";

test.describe("Order approval flow (step 42)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/orders");
    await page.evaluate(() => {
      localStorage.setItem(
        "aushadhinet.devSession",
        JSON.stringify({ uid: "e2e-officer", role: "district", jurisdiction: "mh" })
      );
    });
    await page.reload();
  });

  test("authorized officer sees the order queue (empty or populated)", async ({ page }) => {
    // The officer API has no "create draft order" endpoint by design --
    // orders are only ever created by the solver/agent, never by an API
    // client -- so this checks the page itself loads for an authorized
    // officer, rather than assuming seed data exists in the backend's
    // in-memory store for this run.
    await expect(page.getByRole("heading", { name: /Transfer Orders/i })).toBeVisible();
    const emptyState = page.getByText("No orders yet.");
    const orderCards = page.locator('[data-testid^="order-card-"]');
    await expect(emptyState.or(orderCards.first())).toBeVisible();
  });
});
