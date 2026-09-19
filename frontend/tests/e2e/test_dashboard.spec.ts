import { test, expect } from "@playwright/test";
import { signIn } from "./helpers";

test.describe("Dashboard drill-down", () => {
  test("national -> state -> district -> facility page", async ({ page }) => {
    await signIn(page, "District officer, Nashik");
    await page.getByTestId("map-node-mh").click();
    await expect(page.getByTestId("map-breadcrumb")).toContainText("Maharashtra");
    await page.getByTestId("map-node-mh/nashik").click();
    const facility = page.locator('a[data-testid^="map-node-MH-"]').first();
    await expect(facility).toBeVisible({ timeout: 30_000 });
    await facility.click();
    await expect(page.getByTestId("facility-stock")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("facility-stock")).toContainText("ors");
  });

  test("anonymous users see districts but must sign in for facilities", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("map-node-mh").click();
    await page.getByTestId("map-node-mh/nashik").click();
    await expect(page.getByText("Sign in as an officer (top right) to see facilities.")).toBeVisible();
  });
});
