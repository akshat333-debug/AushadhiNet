import { test, expect } from "@playwright/test";
import { signIn } from "./helpers";

test.describe("Languages", () => {
  test("switching to Marathi translates the UI and WhatsApp replies", async ({ page }) => {
    await page.goto("/sim");
    await page.getByTestId("lang-switcher").selectOption("mr");
    await expect(page.locator("h1")).toHaveText("व्हॉट्सॲप सिम्युलेटर");
    await expect(page.locator("html")).toHaveAttribute("lang", "mr");
    await page.getByTestId("sim-input").fill("ओआरएस 12");
    await page.getByTestId("sim-send").click();
    await expect(page.getByTestId("sim-messages")).toContainText("साठी नोंद केली: ओआरएस 12", { timeout: 30_000 });
  });

  test("the choice persists and the agent answers in Hindi", async ({ page }) => {
    await signIn(page, "District officer, Nashik");
    await page.getByTestId("lang-switcher").selectOption("hi");
    await page.goto("/agent");
    await page.getByRole("button", { name: "MH-0000221 में ओआरएस का जोखिम क्यों है?" }).click();
    await expect(page.getByTestId("agent-chat")).toContainText("अगले सप्ताह ख़त्म होने की संभावना", { timeout: 30_000 });
  });
});
