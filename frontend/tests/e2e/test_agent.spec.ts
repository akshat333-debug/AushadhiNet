import { test, expect } from "@playwright/test";

test.describe("Officer agent chat (step 43)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/agent");
    await page.evaluate(() => {
      localStorage.setItem(
        "aushadhinet.devSession",
        JSON.stringify({ uid: "e2e-officer", role: "district", jurisdiction: "mh" })
      );
    });
    await page.reload();
  });

  test("asking a question shows both the question and an agent reply", async ({ page }) => {
    await page.getByTestId("agent-input").fill("what can you help with?");
    await page.getByTestId("agent-ask").click();
    await expect(page.getByTestId("agent-chat")).toContainText("what can you help with?");
    await expect(page.getByTestId("agent-chat")).toContainText("Agent:");
  });
});
