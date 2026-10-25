import { test, expect } from "@playwright/test";
import { signIn } from "./helpers";

test.describe("Beds and staff", () => {
  test("a nurse reports beds and checks in on WhatsApp; the officer sees beds and staff", async ({ page }) => {
    await page.goto("/sim");
    await expect(page.getByTestId("sim-phone")).not.toHaveValue("");
    await page.getByRole("button", { name: "BEDS 4/6" }).click();
    await expect(page.getByTestId("sim-messages")).toContainText("4 of 6 occupied", { timeout: 30_000 });
    await page.getByTestId("sim-location").click();
    await expect(page.getByTestId("sim-location-bubble").last()).toBeVisible();
    await expect(page.getByTestId("sim-messages")).toContainText("Checked in at", { timeout: 30_000 });

    await signIn(page, "District officer, Nashik");
    await expect(page.getByTestId("capacity-beds")).toContainText("beds in use", { timeout: 30_000 });
    await expect(page.getByTestId("capacity-staff")).toContainText("staff checked in on site");
  });
});
