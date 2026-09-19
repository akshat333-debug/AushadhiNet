import { test, expect } from "@playwright/test";

test.describe("Public transparency view (step 43)", () => {
  test("loads without authentication and shows district-level table", async ({ page }) => {
    await page.goto("/public");
    await expect(page.getByTestId("public-table")).toBeVisible();
  });
});
