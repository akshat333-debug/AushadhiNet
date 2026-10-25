import fs from "node:fs";
import path from "node:path";
import { test, expect } from "@playwright/test";

// A Hindi voice note, "ORS 50, zinc 120", played as the microphone. Chromium's fake capture device
// hangs headless on macOS, so the page's getUserMedia is given a Web Audio stream of the file; the
// app's real MediaRecorder, upload and Chirp transcription all still run.
const VOICE = fs.readFileSync(path.join(__dirname, "fixtures", "voice-hi.wav")).toString("base64");

test.use({ launchOptions: { args: ["--autoplay-policy=no-user-gesture-required"] } });

test.describe("WhatsApp simulator voice note", () => {
  // Local mode answers speech from recorded fixtures, so a live recording is only heard by Chirp in cloud mode.
  test.skip(({ baseURL }) => !baseURL || baseURL.includes("localhost"), "needs the cloud deployment (Chirp)");

  test("a Hindi voice note is transcribed, read as two items and held for YES", async ({ page }) => {
    await page.addInitScript((b64) => {
      navigator.mediaDevices.getUserMedia = async () => {
        const ctx = new AudioContext();
        const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
        const source = ctx.createBufferSource();
        source.buffer = await ctx.decodeAudioData(bytes.buffer);
        const out = ctx.createMediaStreamDestination();
        source.connect(out);
        // Lets the test stop recording when the clip has played, not after a guessed delay.
        (window as unknown as { voiceDone: Promise<unknown> }).voiceDone = new Promise((done) => (source.onended = done));
        source.start();
        return out.stream;
      };
    }, VOICE);
    await page.goto("/sim");
    await expect(page.getByTestId("sim-phone")).not.toHaveValue("");
    await page.getByTestId("sim-voice").click();
    await expect(page.getByTestId("sim-voice")).toHaveAttribute("aria-pressed", "true");
    await page.evaluate(() => (window as unknown as { voiceDone: Promise<unknown> }).voiceDone);
    await page.waitForTimeout(500);
    await page.getByTestId("sim-voice").click();
    await expect(page.getByTestId("sim-voice-bubble").last()).toBeVisible({ timeout: 30_000 });
    const card = page.getByTestId("sim-messages").getByText("Heard in your voice note").last();
    await expect(card).toBeVisible({ timeout: 60_000 });
    await expect(card).toContainText("ORS 50");
    await expect(card).toContainText("120");
  });
});
