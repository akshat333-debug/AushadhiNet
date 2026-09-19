import { test, expect } from "@playwright/test";
import { signIn } from "./helpers";

test.describe("WhatsApp simulator", () => {
  test("a stock report is recorded and acknowledged, and nonsense gets help", async ({ page }) => {
    await page.goto("/sim");
    await expect(page.getByTestId("sim-phone")).not.toHaveValue("");
    await page.getByTestId("sim-input").fill("ORS 7");
    await page.getByTestId("sim-send").click();
    await expect(page.getByTestId("sim-messages")).toContainText("ors-new-who 7", { timeout: 30_000 });
    await page.getByTestId("sim-input").fill("hello");
    await page.getByTestId("sim-send").click();
    await expect(page.getByTestId("sim-messages")).toContainText("Could not read that");
  });

  test("a report shows up on the facility page for the district officer", async ({ page }) => {
    await page.goto("/sim");
    await page.getByTestId("sim-phone").selectOption({ index: 1 });
    const facilityId = (await page.getByTestId("sim-phone").locator("option:checked").innerText()).match(/MH-\d{7}/)![0];
    await page.getByTestId("sim-input").fill("Zinc 3");
    await page.getByTestId("sim-send").click();
    await expect(page.getByTestId("sim-messages")).toContainText("Recorded for", { timeout: 30_000 });

    await signIn(page, "District officer, Nashik");
    await page.goto(`/facility/${facilityId}`);
    const row = page.getByTestId("facility-stock").locator("tr", { hasText: "zinc-sulphate" });
    await expect(row.locator("td").nth(1)).toHaveText("3", { timeout: 30_000 });
  });
});
