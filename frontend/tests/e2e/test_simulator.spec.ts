import { test, expect } from "@playwright/test";
import { signIn } from "./helpers";

test.describe("WhatsApp simulator", () => {
  test("a stock report is recorded and acknowledged, and nonsense gets help", async ({ page }) => {
    await page.goto("/sim");
    await expect(page.getByTestId("sim-phone")).not.toHaveValue("");
    // Unique quantity: a long-lived server keeps earlier runs' replies in the outbox.
    const qty = 100 + (Date.now() % 800);
    await page.getByTestId("sim-input").fill(`ORS ${qty}`);
    await page.getByTestId("sim-send").click();
    await expect(page.getByTestId("sim-messages")).toContainText(`: ORS ${qty}.`, { timeout: 30_000 });
    const help = page.getByTestId("sim-messages").getByText("Could not read that");
    const before = await help.count();
    await page.getByTestId("sim-input").fill("hello");
    await page.getByTestId("sim-send").click();
    await expect(help).toHaveCount(before + 1, { timeout: 30_000 });
  });

  test("a report shows up on the facility page for the district officer", async ({ page }) => {
    await page.goto("/sim");
    await page.getByTestId("sim-phone").selectOption({ index: 1 });
    const facilityId = (await page.getByTestId("sim-phone").locator("option:checked").innerText()).match(/MH-\d{7}/)![0];
    const qty = 100 + (Date.now() % 800);
    await page.getByTestId("sim-input").fill(`Zinc ${qty}`);
    await page.getByTestId("sim-send").click();
    await expect(page.getByTestId("sim-messages")).toContainText(`Zinc 20 mg tablet ${qty}.`, { timeout: 30_000 });

    await signIn(page, "District officer, Nashik");
    await page.goto(`/facility/${facilityId}`);
    const row = page.getByTestId("facility-stock").locator("tr", { hasText: "Zinc 20 mg tablet" });
    await expect(row.locator("td").nth(1)).toHaveText(String(qty), { timeout: 30_000 });
  });
});
