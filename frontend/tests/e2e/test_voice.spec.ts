import path from "node:path";
import { test, expect } from "@playwright/test";

// Chromium plays this WAV as the microphone: a Hindi voice note, "ORS 50, zinc 120".
const VOICE = path.join(__dirname, "fixtures", "voice-hi.wav");

test.use({
  permissions: ["microphone"],
  launchOptions: { args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", `--use-file-for-fake-audio-capture=${VOICE}`] },
});

test.describe("WhatsApp simulator voice note", () => {
  // Local mode answers speech from recorded fixtures, so a live recording is only heard by Chirp in cloud mode.
  test.skip(({ baseURL }) => !baseURL || baseURL.includes("localhost"), "needs the cloud deployment (Chirp)");

  test("a Hindi voice note is transcribed, read as two items and held for YES", async ({ page }) => {
    await page.goto("/sim");
    await expect(page.getByTestId("sim-phone")).not.toHaveValue("");
    await page.getByTestId("sim-voice").click();
    await page.waitForTimeout(4_000);
    await page.getByTestId("sim-voice").click();
    await expect(page.getByTestId("sim-voice-bubble").last()).toBeVisible();
    const card = page.getByTestId("sim-messages").getByText("Heard in your voice note").last();
    await expect(card).toBeVisible({ timeout: 60_000 });
    await expect(card).toContainText("ORS 50");
    await expect(card).toContainText("120");
  });
});
