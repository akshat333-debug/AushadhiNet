import { test, expect } from "@playwright/test";

test.describe("WhatsApp simulator (step 40)", () => {
  test("sending a message queues it and shows an ack", async ({ page }) => {
    await page.goto("/sim");
    await page.getByTestId("sim-input").fill("ORS 50");
    await page.getByTestId("sim-send").click();
    await expect(page.getByTestId("sim-messages")).toContainText("ORS 50");
    await expect(page.getByTestId("sim-messages")).toContainText("Queued for processing.");
  });
});
