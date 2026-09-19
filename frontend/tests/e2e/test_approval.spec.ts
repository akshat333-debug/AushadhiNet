import { test, expect } from "@playwright/test";
import { signIn } from "./helpers";

test.describe("Order approval", () => {
  test("anonymous users are asked to sign in", async ({ page }) => {
    await page.goto("/orders");
    await expect(page.getByText(/Sign in as a block, district or state officer/)).toBeVisible();
  });

  test("propose drafts, approve one, and it leaves the draft queue as approved", async ({ page }) => {
    await signIn(page, "District officer, Nashik");
    await page.goto("/orders");
    await page.getByTestId("propose").click();
    await expect(page.getByTestId("notice")).toContainText("draft transfer(s) proposed", { timeout: 60_000 });
    const approve = page.locator('[data-testid^="approve-"]').first();
    const orderId = (await approve.getAttribute("data-testid"))!.replace("approve-", "");
    await approve.click();
    await expect(page.getByTestId(`order-card-${orderId}`)).toHaveCount(0);
    await page.locator("main select").selectOption("all");
    await expect(page.getByTestId(`order-status-${orderId}`)).toHaveText("approved");
  });
});
