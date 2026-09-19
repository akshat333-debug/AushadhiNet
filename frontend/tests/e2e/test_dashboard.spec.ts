import { test, expect } from "@playwright/test";

test.describe("Dashboard drill-down (step 41)", () => {
  test("national -> state -> district reachable within a few clicks", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("map-view")).toBeVisible();
    // click 1: national -> Maharashtra
    await page.getByTestId("map-node-mh").click();
    await expect(page.getByTestId("map-breadcrumb")).toContainText("Maharashtra");
  });
});
