import { test, expect } from "@playwright/test";

test.describe("Public transparency view", () => {
  test("loads without authentication, shows districts and no facility IDs", async ({ page }) => {
    await page.goto("/public");
    await expect(page.getByTestId("public-table")).toContainText("mh/nashik");
    await expect(page.getByTestId("public-table")).not.toContainText("MH-00");
  });
});
